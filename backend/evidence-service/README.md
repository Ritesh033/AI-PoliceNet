# Evidence Service

Manages digital evidence with secure storage, hash verification, and chain-of-custody tracking.

## Features
- **Uploads**: Secure file upload (video, audio, images, documents)
- **Hashing**: SHA-256 hash generation for evidence integrity
- **Metadata**: Extraction and storage of file metadata (date, location, device)
- **Chain of Custody**: Immutable record of who accessed evidence and when
- **Evidence Search**: Full-text and metadata-based search

## Evidence Workflow
1. Upload → Hash generated → Metadata extracted
2. Evidence marked as **Temporary Review Evidence**
3. Citizen has 3-5 days to upload complete evidence
4. Moderator + AI verify authenticity
5. Verified → **Permanent Evidence** (used in investigation/court)
6. Rejected → Flagged with reason

## Supported Formats
- Video: MP4, AVI, MOV, WebM
- Audio: MP3, WAV, OGG, M4A
- Image: JPEG, PNG, BMP, TIFF
- Document: PDF, DOCX

## Storage
- AWS S3 with server-side encryption
- MongoDB for metadata
- Blockchain ledger for hash records

## Port: 8004
