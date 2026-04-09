# aws-s3-secure-backup-tool
Secure automated backup tool that encrypts files locally before uploading to AWS S3.

# Secure S3 Backup Tool
A Python-based automated backup tool that securely encrypts files before uploading them to AWS S3.
This tool demonstrates cloud automation, security best practices, and Python scripting skills.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![boto3](https://img.shields.io/badge/boto3-FF9900?style=for-the-badge&logo=amazon&logoColor=white)

## Features

- **End-to-end encryption** — Files are encrypted locally using Fernet (symmetric encryption) before upload
- **Automated backups** — Walks through folders and subfolders recursively
- **Timestamped backups** — Each backup gets its own dated folder in S3
- **Presigned URLs** — Generates temporary secure download links (1 hour for encrypted, 1 hour for decrypted share) (Modifiable)
- **Automatic cleanup** — Old temporary share files are automatically deleted after expiration
- **Decryption script** — Separate tool to download and decrypt files locally

## Technologies Used

- Python 3
- boto3 (AWS SDK for Python)
- cryptography.fernet (secure encryption)
- AWS S3
- IAM (for secure access)

## How to Use

### 1. Setup
   ```bash
      pip install boto3 cryptography
   ```
### 2. Configuration
      Open back0p.py and update the following in the CONFIG section:AWS_ACCESS_KEY and AWS_SECRET_KEY (use your IAM user keys)
      BUCKET_NAME (your S3 bucket name)
      FOLDER_TO_BACKUP (the folder on your computer you want to backup)
      REGION (aws region)
      FOLDER_TO_BACKUP (Windows and macOS paths are available) 
      SHARE_EXPIRATION (in seconds, 3600 is 1h)

### 3. Run Backup
  	 python3 back0p.py
 
   The script will:
   * Encrypt all files in the selected folder using secure Fernet encryption
   * Upload the encrypted files to AWS S3 with timestamped folders
   * Generate and display temporary presigned URLs
   * Encrypted link (1 hour validity), Decrypted share link (1 hour validity)

### 4. Decrypt a Downloaded File
   ```bash
      python3 decrypt.py
   ```
    Update the S3_KEY variable in decrypt_from_s3.py with the path of the encrypted file you want to decrypt (from the backups/ folder).
   * The script will download the encrypted file, decrypt it, and save the original file locally.






