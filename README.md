# aws-s3-secure-backup-tool

Secure automated backup tool that encrypts files locally before uploading to AWS S3.

# Secure S3 Backup Tool

A Python-based automated backup tool that securely encrypts files before uploading them to AWS S3.
This tool demonstrates cloud automation, security best practices, and Python scripting skills.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![boto3](https://img.shields.io/badge/boto3-FF9900?style=for-the-badge&logo=amazon&logoColor=white)

## Features

- **End-to-end encryption** — Files are encrypted locally using Fernet (symmetric encryption) before upload. Plaintext data never touches S3.
- **Automated backups** — Walks through folders and subfolders recursively
- **Timestamped backups** — Each backup gets its own dated folder in S3
- **Presigned URLs** — Generates a temporary secure download link per file (configurable expiration, default 1 hour)
- **Per-file error handling** — Failed uploads are caught individually; a summary is printed at the end
- **Decryption script** — Separate tool to download and decrypt files locally

## Technologies Used

- Python 3
- boto3 (AWS SDK for Python)
- cryptography.fernet (symmetric encryption)
- python-dotenv (environment-based configuration)
- AWS S3
- IAM (for secure access)

## Project Structure

```
aws-s3-secure-backup-tool/
├── back0p.py           # Main backup script
├── decrypt.py          # Download and decrypt a file from S3
├── keys.env            # Your credentials and config (never commit this)
├── encryption_key.key  # Auto-generated on first run (never commit this)
└── .gitignore          # Should exclude keys.env and encryption_key.key
```

## Setup

### 1. Install dependencies

```bash
pip install boto3 cryptography python-dotenv
```

### 2. Configure `keys.env`

All configuration is done through a `keys.env` file in the project root. Never commit this file.

```env
# === AWS Credentials (required) ===
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# === AWS S3 Settings ===
BUCKET_NAME=your-bucket-name
REGION=your-region

# === Local Backup Settings ===
# On Mac/Linux: ~/Documents/MyFolder
# On Windows:   C:\Users\YourName\MyFolder
FOLDER_TO_BACKUP=~/Documents/your-folder

# === Presigned URL Expiration ===
# How long the download link stays valid (in seconds), 3600 = 1 hour
SHARE_EXPIRATION=3600

# === Decrypt script settings ===
# Set this before running decrypt.py
S3_KEY=backups/YYYY-MM-DD_HH-MM-SS/yourfile.ext
```

### 3. Add a `.gitignore`

Make sure your repo includes a `.gitignore` to avoid accidentally committing secrets:

```
keys.env
encryption_key.key
*.key
.env
```

## How to Use

### Run a Backup

```bash
python3 backup.py
```

The script will:
- Encrypt every file in the configured folder using Fernet encryption
- Upload only the encrypted files to AWS S3 under a timestamped prefix (`backups/YYYY-MM-DD_HH-MM-SS/`)
- Generate and print a presigned download URL for each file
- Print a summary of succeeded and failed uploads

> **Sharing files:** To share a backup file, send the presigned URL along with the `encryption_key.key` file through a separate secure channel. The recipient can then use `decrypt.py` to decrypt it.

### Decrypt a File

1. Set `S3_KEY` in `keys.env` to the path of the file you want to decrypt (e.g. `backups/2026-04-09_21-27-35/photo.jpg`)
2. Run:

```bash
python3 decrypt.py
```

The script will download the encrypted file from S3, decrypt it using your local `encryption_key.key`, and save it with its original filename in the current directory.

## Security Notes

- **Plaintext data never leaves your machine** — only encrypted files are uploaded to S3
- **Credentials are loaded from `keys.env`** — never hardcoded in source files
- **The encryption key (`encryption_key.key`) is generated automatically** on first run and reused on subsequent runs. Keep it safe — without it, your backups cannot be decrypted
- It is recommended to use an IAM user with least-privilege permissions (S3 read/write on your bucket only)
