from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.core.audit import AuditLogService
from app.core.file_validator import validate_medical_file_upload
from app.db.supabase_client import SIGNED_URL_TTL_SECONDS, generate_private_wallet_signed_url
from app.models.schemas import UserRole


def test_file_validator_accepts_valid_pdf_and_jpeg_magic_bytes():
    valid_pdf = b"%PDF-1.7\n%sample medical report content"
    valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"

    assert validate_medical_file_upload(valid_pdf, "application/pdf") == "application/pdf"
    assert validate_medical_file_upload(valid_jpeg, "image/jpeg") == "image/jpeg"


def test_file_validator_blocks_spoofed_executable_disguised_as_image():
    # Attacker renames malware.exe (MZ header) to prescription.jpg
    spoofed_exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00malicious_payload"

    with pytest.raises(HTTPException) as exc:
        validate_medical_file_upload(spoofed_exe_bytes, "image/jpeg")
    assert exc.value.status_code == 400
    assert "binary signature" in exc.value.detail


def test_file_validator_blocks_oversized_files():
    oversized_pdf = b"%PDF-" + (b"0" * (6 * 1024 * 1024))  # 6 MB (> 5 MB limit)

    with pytest.raises(HTTPException) as exc:
        validate_medical_file_upload(oversized_pdf, "application/pdf")
    assert exc.value.status_code == 413


def test_audit_log_service_records_immutable_entry_and_has_no_delete():
    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "log_1", "action_summary": "Dr. Patil added Amlodipine 5mg"}
    ]

    audit_service = AuditLogService(mock_db)

    # Verify strict append-only design: service must not have delete or update methods
    assert not hasattr(audit_service, "delete_event")
    assert not hasattr(audit_service, "update_event")

    result = audit_service.record_event(
        patient_id="pat_555",
        actor_id="doc_101",
        actor_role=UserRole.DOCTOR,
        action_summary="Dr. Patil added Amlodipine 5mg",
        previous_state=None,
        new_state={"medication": "Amlodipine 5mg"},
    )
    assert result["action_summary"] == "Dr. Patil added Amlodipine 5mg"
    mock_db.table.assert_called_once_with("audit_logs")


def test_private_wallet_signed_url_enforces_60_second_ttl():
    mock_storage = MagicMock()
    mock_storage.from_.return_value.create_signed_url.return_value = {
        "signedURL": "https://project.supabase.co/storage/v1/object/sign/health-wallet-private/pat_555/report.pdf?token=xyz"
    }

    url = generate_private_wallet_signed_url(mock_storage, "pat_555/report.pdf")
    assert "token=xyz" in url
    mock_storage.from_.return_value.create_signed_url.assert_called_once_with(
        "pat_555/report.pdf", SIGNED_URL_TTL_SECONDS
    )
    assert SIGNED_URL_TTL_SECONDS == 60