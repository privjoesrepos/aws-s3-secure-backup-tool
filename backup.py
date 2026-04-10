import boto3
import os
import json
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

# ===================================================
load_dotenv("keys.env")

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME    = os.environ.get("BUCKET_NAME")
REGION         = os.environ.get("REGION")

if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
    raise ValueError("❌ Missing AWS credentials! Check your keys.env file.")
if not BUCKET_NAME or not REGION:
    raise ValueError("❌ Missing BUCKET_NAME or REGION in keys.env file!")

# ===================================================
_folder_raw = os.environ.get("FOLDER_TO_BACKUP")
if not _folder_raw:
    raise ValueError("❌ Missing FOLDER_TO_BACKUP in keys.env file!")

FOLDER_TO_BACKUP = os.path.expanduser(_folder_raw)
SHARE_EXPIRATION = int(os.environ.get("SHARE_EXPIRATION", 3600))

MAX_WORKERS = max(1, int(os.environ.get("MAX_WORKERS", "12")))
MAX_RETRIES = max(0, int(os.environ.get("MAX_RETRIES", "3")))

SHOW_PER_FILE_PROGRESS = os.environ.get("SHOW_PER_FILE_PROGRESS")
if SHOW_PER_FILE_PROGRESS is None:
    SHOW_PER_FILE_PROGRESS = MAX_WORKERS <= 4
else:
    SHOW_PER_FILE_PROGRESS = str(SHOW_PER_FILE_PROGRESS).strip() == "1"

if not os.path.exists(FOLDER_TO_BACKUP) or not os.path.isdir(FOLDER_TO_BACKUP):
    raise ValueError(f"❌ Folder not found or is not a directory: {FOLDER_TO_BACKUP}")

# ===================================================
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
            key = f.read()
        if len(key) != 32:
            raise ValueError("❌ encryption_key.key must be exactly 32 bytes (AES-256 key).")
        return key
    else:
        key = os.urandom(32)
        with open(key_file, "wb") as f:
            f.write(key)
        print("✅ New 32-byte AES-256 encryption key generated and saved.")
        return key

key = get_or_create_key()

console_lock = threading.Lock()

def make_callback(pbar):
    def callback(bytes_transferred):
        with console_lock:
            pbar.update(bytes_transferred)
    return callback

def process_single_file(file_path: str, relative_path: str, s3_key: str):
    """Encrypt once → retry upload only."""
    chunk_size = 64 * 1024 * 1024

    try:
        with open(file_path, "rb") as f_in:
            with tempfile.TemporaryFile() as f_enc:
                if not SHOW_PER_FILE_PROGRESS:
                    print(f"🔐 Encrypting: {relative_path}")

                nonce = os.urandom(12)
                f_enc.write(nonce)

                cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
                encryptor = cipher.encryptor()

                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_enc.write(encryptor.update(chunk))

                encryptor.finalize()
                f_enc.write(encryptor.tag)

                f_enc.seek(0, 2)
                encrypted_size = f_enc.tell()

                for attempt in range(MAX_RETRIES + 1):
                    f_enc.seek(0)
                    attempt_label = f" (retry {attempt})" if attempt > 0 else ""

                    try:
                        if SHOW_PER_FILE_PROGRESS:
                            with tqdm(
                                total=encrypted_size,
                                unit='B',
                                unit_scale=True,
                                unit_divisor=1024,
                                desc=f"↑ {relative_path}",
                                leave=False,
                                position=None,
                                mininterval=0.5
                            ) as pbar:
                                s3.upload_fileobj(
                                    f_enc,
                                    BUCKET_NAME,
                                    s3_key,
                                    Callback=make_callback(pbar)
                                )
                        else:
                            print(f"⬆️  Uploading{attempt_label}: {relative_path} ({encrypted_size:,} bytes)")
                            s3.upload_fileobj(f_enc, BUCKET_NAME, s3_key)

                        break

                    except Exception as e:
                        if attempt == MAX_RETRIES:
                            raise RuntimeError(f"Upload failed for {relative_path} after {MAX_RETRIES} retries: {e}") from e
                        wait = 2 ** attempt
                        print(f"⚠️  Attempt {attempt+1}/{MAX_RETRIES+1} failed — retrying in {wait}s...")
                        time.sleep(wait)

                presigned_url = s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
                    ExpiresIn=SHARE_EXPIRATION
                )

                return {
                    "s3_key": s3_key,
                    "presigned_url": presigned_url,
                    "original_size_bytes": os.path.getsize(file_path)
                }

    except Exception as e:
        raise RuntimeError(f"Failed {relative_path}: {e}") from e


def backup_folder():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print(f"🚀 Starting PARALLEL backup at {timestamp}... "
          f"(max {MAX_WORKERS} threads | {MAX_RETRIES} upload retries per file)\n")

    files_to_process = []
    for root, dirs, files in os.walk(FOLDER_TO_BACKUP, followlinks=False):
        for file in files:
            file_path     = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, FOLDER_TO_BACKUP)
            s3_key        = f"backups/{timestamp}/{relative_path}"
            files_to_process.append((file_path, relative_path, s3_key))

    print(f"📦 Found {len(files_to_process)} files to backup.\n")

    success = []
    failed = []
    manifest = {
        "backup_timestamp": timestamp,
        "source_folder": FOLDER_TO_BACKUP,
        "encryption": "AES-256-GCM (12-byte nonce + ciphertext + 16-byte tag)",
        "files": {}
    }

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_info = {
            executor.submit(process_single_file, fp, rp, sk): (fp, rp)
            for fp, rp, sk in files_to_process
        }

        with tqdm(total=len(files_to_process), desc="Files completed", unit="file") as pbar:
            for future in as_completed(future_to_info):
                fp, rp = future_to_info[future]
                try:
                    manifest_entry = future.result()
                    manifest["files"][rp] = manifest_entry
                    success.append(fp)
                except Exception as e:
                    print(f"❌ {e}")
                    failed.append(fp)
                pbar.update(1)

    if manifest["files"]:
        manifest_key = f"backups/{timestamp}/MANIFEST.json"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=manifest_key,
            Body=json.dumps(manifest, indent=2).encode('utf-8')
        )

        manifest_presigned = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': manifest_key},
            ExpiresIn=SHARE_EXPIRATION
        )

        print(f"\n📋 Manifest created with {len(manifest['files'])} files")
        print(f"🔗 Manifest Download Link ({SHARE_EXPIRATION}s):")
        print(manifest_presigned)

    print(f"\n--- Backup Complete ---")
    print(f"✅ Succeeded: {len(success)} files")
    print(f"❌ Failed:    {len(failed)} files")
    if failed:
        for f in failed:
            print(f"   - {f}")

if __name__ == "__main__":
    backup_folder()
