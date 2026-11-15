from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.security import (
    create_Scoped_doctor_token,
    create_user_access_token,
    decode_access_token,
    generate_six_digit_pin,
    hash_pin,
    is_pin_expired,
    verify_doctor_scope,
    verify_patient_resource_access,
    verify_pin_hash,
)
from app.models.schemas import (
    MedicationItemSchema,
    PinVerificationRequest,
    PrescriptionCreateSchema,
    SOSTriggerRequest,
)


def test_pin_generation_and_bcrypt_verification():
    pin = generate_six_digit_pin()
    assert len(pin) == 6
    assert pin.isdigit()

    hashed = hash_pin(pin)
    assert hashed != pin
    assert verify_pin_hash(pin, hashed) is True
    assert verify_pin_hash("000000", hashed) is False


def test_pin_expiration_window():
    valid_future = datetime.now(timezone.utc) + timedelta(minutes=10)
    expired_past = datetime.now(timezone.utc) - timedelta(minutes=1)

    assert is_pin_expired(valid_future) is False
    assert is_pin_expired(expired_past) is True


def test_scoped_doctor_token_and_permissions():
    token = create_Scoped_doctor_token(doctor_id="doc_101", target_patient_id="pat_555")
    payload = decode_access_token(token)

    assert payload["role"] == "DOCTOR"
    assert payload["target_patient_id"] == "pat_555"
    assert verify_doctor_scope(payload, "wallet:read") is True
    assert verify_doctor_scope(payload, "prescription:create") is True
    assert verify_doctor_scope(payload, "first_aid:write") is True

    # Doctor must NEVER have delete scope
    with pytest.raises(HTTPException) as exc:
        verify_doctor_scope(payload, "wallet:delete")
    assert exc.value.status_code == 403


def test_expired_jwt_rejected():
    expired_token = create_Scoped_doctor_token(
        doctor_id="doc_101",
        target_patient_id="pat_555",
        expires_delta=timedelta(seconds=-5),
    )
    with pytest.raises(HTTPException) as exc:
        decode_access_token(expired_token)
    assert exc.value.status_code == 401


def test_bola_protection_blocks_unauthorized_patient_access():
    # Caretaker linked only to pat_555 tries to access pat_999
    caretaker_token = create_user_access_token(
        user_id="care_1", role="CARETAKER", linked_patient_ids=["pat_555"]
    )
    payload = decode_access_token(caretaker_token)

    # Allowed for linked patient
    assert verify_patient_resource_access(payload, "pat_555") is True

    # Blocked (403 Forbidden) for unlinked patient
    with pytest.raises(HTTPException) as exc:
        verify_patient_resource_access(payload, "pat_999")
    assert exc.value.status_code == 403


def test_pydantic_rejects_malformed_pin_and_invalid_coordinates():
    # Letters in PIN should fail regex validation
    with pytest.raises(ValidationError):
        PinVerificationRequest(patient_id="pat_1", doctor_id="doc_1", pin="12AB56")

    # Invalid GPS latitude (> 90) should fail SOS schema validation
    with pytest.raises(ValidationError):
        SOSTriggerRequest(
            patient_id="pat_1",
            triggered_via="VOICE_AMBULANCE",
            latitude=145.0,
            longitude=73.8567,
            countdown_completed=True,
        )


def test_prescription_schema_validates_structured_course():
    rx = PrescriptionCreateSchema(
        diagnosis_notes="Mild hypertension",
        medications=[
            MedicationItemSchema(
                name="Amlodipine",
                dosage="5mg",
                morning=True,
                afternoon=False,
                evening=True,
                duration_days=30,
            )
        ],
    )
    assert len(rx.medications) == 1
    assert rx.medications[0].morning is True