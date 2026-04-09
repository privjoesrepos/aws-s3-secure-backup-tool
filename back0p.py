import boto3
import os
import io
from cryptography.fernet import Fernet
from datetime import datetime
from dotenv import load_dotenv
# ==================================================
load_dotenv("keys.env")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
    raise ValueError("Missing AWS credentials! Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY as environment variables.")
# ===================== CONFIG =======================
BUCKET_NAME = ""
REGION = ""
#FOLDER_TO_BACKUP = r"*****"              #windows
FOLDER_TO_BACKUP = os.path.expanduser("") #macOS
SHARE_EXPIRATION = 3600                   # 1 hour in seconds
# =========================================================

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION,
    config=boto3.session.Config(
        signature_version='s3v4',
        s3={'addressing_style': 'virtual'}
    )
)

def get_or_create_key():
    key_file = "encryption_key.key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
        print("New encryption key generated and saved.")
        return key

key    = get_or_create_key()
cipher = Fernet(key)

def cleanup_old_share_files():
    print("Cleaning up old share files...")
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix="share/")
        if 'Contents' not in response:
            return
        now = datetime.utcnow()
        for obj in response['Contents']:
            last_modified = obj['LastModified'].replace(tzinfo=None)
            age = (now - last_modified).total_seconds()
            if age > SHARE_EXPIRATION:
                s3.delete_object(Bucket=BUCKET_NAME, Key=obj['Key'])
                print(f"Deleted old share file: {obj['Key']}")
    except Exception as e:
        print(f"Cleanup failed: {e}")

def backup_folder():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print(f"Starting backup at {timestamp}...\n")
    cleanup_old_share_files()

    success = []
    failed  = []

    for root, dirs, files in os.walk(FOLDER_TO_BACKUP):
        for file in files:
            file_path     = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, FOLDER_TO_BACKUP)
            s3_key        = f"backups/{timestamp}/{relative_path}"

            try:
                with open(file_path, "rb") as f:
                    data = f.read()

                encrypted_data = cipher.encrypt(data)
                file_obj       = io.BytesIO(encrypted_data)  

                s3.upload_fileobj(file_obj, BUCKET_NAME, s3_key)
                print(f"✅ Uploaded: {s3_key}")

                encrypted_url = s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
                    ExpiresIn=3600
                )
                print(f"Encrypted Link (1 hour):\n{encrypted_url}\n")

                share_key  = f"share/{timestamp}/{relative_path}"
                share_obj  = io.BytesIO(data)  
                s3.upload_fileobj(share_obj, BUCKET_NAME, share_key)

                decrypted_url = s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME, 'Key': share_key},
                    ExpiresIn=SHARE_EXPIRATION
                )
                print(f"Decrypted Share Link (1 hour):\n{decrypted_url}\n")

                success.append(file_path)

            except Exception as e:
                print(f"❌ Failed: {file_path} — {e}")
                failed.append(file_path)

    print(f"\n--- Backup Complete ---")
    print(f"✅ Succeeded: {len(success)} files")
    print(f"❌ Failed:    {len(failed)} files")
    if failed:
        for f in failed:
            print(f"   - {f}")

if __name__ == "__main__":
    backup_folder()
