import boto3
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv
# ==========================================
load_dotenv("keys.env")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
    raise ValueError("Missing AWS credentials! Check your keys.env file.")
# ===================== CONFIG =======================
BUCKET_NAME = ""
REGION = ""
# Change this to the exact key of the file you want to download
S3_KEY = "backups/2026-04-09_02-03-00/wallpaperflare.com_wallpaper.jpg"
# ====================================================

OUTPUT_FILENAME = os.path.basename(S3_KEY) if S3_KEY else "decrypted_output"

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION
)

with open("encryption_key.key", "rb") as f:
    key = f.read()

cipher = Fernet(key)

def download_and_decrypt():
    if not S3_KEY:
        print("❌ Please set S3_KEY in the CONFIG section.")
        return

    try:
        print(f"Downloading encrypted file: {S3_KEY}")
        response       = s3.get_object(Bucket=BUCKET_NAME, Key=S3_KEY)
        encrypted_data = response['Body'].read()

        decrypted_data = cipher.decrypt(encrypted_data)

        with open(OUTPUT_FILENAME, "wb") as f:
            f.write(decrypted_data)

        print(f"✅ Decrypted and saved as: {OUTPUT_FILENAME}")

    except Exception as e:
        print(f"❌ Failed to decrypt: {e}")

download_and_decrypt()
