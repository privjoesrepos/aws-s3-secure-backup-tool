# AWS S3 Secure Backup Tool

Secure automated backup tool that **encrypts files locally** before uploading to AWS S3.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![boto3](https://img.shields.io/badge/boto3-FF9900?style=for-the-badge&logo=amazon&logoColor=white)

A robust Python backup solution that encrypts files using **AES-256-GCM** before uploading them to AWS S3. Designed for security, performance, and ease of restoration.

---

## What's New in v2

- **True streaming AES-256-GCM encryption** — Low memory usage even for large files
- **Parallel uploads & downloads** — Configurable concurrency with `ThreadPoolExecutor`
- **Smart retry logic** — Automatic retries with exponential backoff on transient failures
- **Manifest-based restore** — Full folder restore using `MANIFEST.json`
- **Path traversal protection** — Safe restoration even from untrusted manifests
- **Clean progress reporting** — Improved console output with `tqdm`

---

## Features

- **End-to-end encryption** — Files are encrypted locally with AES-256-GCM (authenticated encryption). Plaintext never touches S3.
- **Streaming processing** — Low memory footprint; suitable for large files and folders.
- **Timestamped backups** — Each run creates a unique folder: `backups/YYYY-MM-DD_HH-MM-SS/`
- **Manifest file** — `MANIFEST.json` contains metadata, presigned URLs, and original sizes.
- **Parallel operations** — Fast backup and restore with configurable worker count.
- **Retry resilience** — Handles transient S3/network errors gracefully.
- **Two restore modes** — Full folder restore by timestamp or single file decrypt.

---

## Technologies Used

- Python 3
- boto3 (AWS SDK)
- cryptography (AES-256-GCM via `hazmat`)
- python-dotenv
- tqdm (progress bars)
- AWS S3

---

## Setup

### 1. Install dependencies

```bash
pip3 install boto3 cryptography python-dotenv tqdm
```

### 2. Configure `keys.env`

Copy `keys.env.example` to `keys.env` and fill in your details.

### 3. First Run

The first time you run the backup script, it will automatically generate `encryption_key.key`. Keep this file safe — it is required to decrypt your backups.

---

## How to Use

### 1. Run a Backup

```bash
python3 backup.py
```

### 2. Restore an Entire Backup

Set `RESTORE_TIMESTAMP` in `keys.env`, then run:

```bash
python3 decrypt_restore.py
```

### 3. Decrypt a Single File

Uncomment and set `S3_KEY` in `keys.env`, then run:

```bash
python3 decrypt_restore.py
```

---

## Security Notes

- Plaintext data never leaves your machine — only encrypted files are uploaded to S3.
- AES-256-GCM provides both confidentiality and integrity.
- Keep `encryption_key.key` safe — losing it means your backups become permanently unrecoverable.
- Use an IAM user with least-privilege permissions (S3 access only).

---

## Changelog

### v2.0.0 (Current)

- Upgraded from Fernet to AES-256-GCM streaming encryption
- Added true low-memory streaming for backup and restore
- Parallel processing with thread-safe progress bars
- Added `MANIFEST.json`, retry logic, and path traversal protection
- Improved console output and error handling

### v1.0.0

- Initial Fernet-based implementation
