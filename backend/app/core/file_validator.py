from fastapi import HTTPException, status

MAX_WALLET_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB limit

# Magic byte signatures for allowed medical document formats
MAGIC_SIGNATURES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "application/pdf": [b"%PDF-"],
}


def validate_medical_file_upload(file_bytes: bytes, declared_content_type: str) -> str:
    """
    Validates file size and verifies binary magic bytes against declared MIME type.
    Prevents malicious scripts disguised as images or PDFs.
    """
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(file_bytes) > MAX_WALLET_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File exceeds the 5 MB maximum size limit.",
        )

    if declared_content_type not in MAGIC_SIGNATURES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {declared_content_type}. Only JPEG, PNG, and PDF are allowed.",
        )

    expected_signatures = MAGIC_SIGNATURES[declared_content_type]
    if not any(file_bytes.startswith(sig) for sig in expected_signatures):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security Alert: File binary signature does not match declared MIME type.",
        )

    return declared_content_type