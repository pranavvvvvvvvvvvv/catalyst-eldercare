from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import (
    create_Scoped_doctor_token,
    decode_access_token,
    generate_six_digit_pin,
    hash_pin,
    is_pin_expired,
    verify_doctor_scope,
    verify_patient_resource_access,
    verify_pin_hash,
)
from app.models.schemas import (
    DoctorSessionResponse,
    EmergencyFirstAidSchema,
    LanguageCode,
    MealTiming,
    PinVerificationRequest,
    PrescriptionCreateSchema,
    SOSTriggerRequest,
)
from app.services.google_services import (
    build_first_aid_local_voice_cache,
    build_google_calendar_appointment_sync,
    generate_vernacular_voice_readout,
    parse_doctor_dictation_with_gemini,
)

router = APIRouter(prefix="/api/v1")

_ACTIVE_PINS: Dict[str, Dict[str, Any]] = {}
_PIN_ATTEMPTS: Dict[str, int] = {}
_PATIENT_FIRST_AID: Dict[str, Dict[str, Any]] = {}
_PATIENT_PRESCRIPTIONS: Dict[str, list] = {}
_PATIENT_LANGUAGES: Dict[str, LanguageCode] = {}
_AUDIT_TRAIL: Dict[str, list] = {}


def get_current_token_payload(authorization: str = Header(...)) -> Dict[str, Any]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = authorization.replace("Bearer ", "", 1).strip()
    return decode_access_token(token)


class DictationRequest(BaseModel):
    transcript: str = Field(..., min_length=5, max_length=2000)


class LanguageToggleRequest(BaseModel):
    preferred_language: LanguageCode


# --- 1. PATIENT LANGUAGE TOGGLE (EN / HI / MR) ---

@router.put("/patient/{patient_id}/language")
def toggle_patient_language(
    patient_id: str,
    body: LanguageToggleRequest,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_patient_resource_access(token_payload, patient_id)
    _PATIENT_LANGUAGES[patient_id] = body.preferred_language

    # Return pre-cached First-Aid voice in the newly toggled language if a doctor has set one
    first_aid_record = _PATIENT_FIRST_AID.get(patient_id)
    local_first_aid_voice = None
    if first_aid_record and "cached_local_voice" in first_aid_record:
        local_first_aid_voice = first_aid_record["cached_local_voice"].get(body.preferred_language.value)

    return {
        "patient_id": patient_id,
        "preferred_language": body.preferred_language.value,
        "cached_first_aid_voice": local_first_aid_voice,
    }


# --- 2. PATIENT GENERATES 15-MINUTE ONE-TIME CONSULTATION PIN/QR ---

@router.post("/patient/{patient_id}/generate-pin")
def generate_consultation_pin(
    patient_id: str,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_patient_resource_access(token_payload, patient_id)
    raw_pin = generate_six_digit_pin()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PIN_EXPIRE_MINUTES)

    _ACTIVE_PINS[patient_id] = {
        "pin_hash": hash_pin(raw_pin),
        "expires_at": expires_at,
        "is_used": False,
    }
    _PIN_ATTEMPTS[patient_id] = 0

    return {
        "patient_id": patient_id,
        "consultation_pin": raw_pin,
        "qr_payload": f"eldercare://verify?patient_id={patient_id}&pin={raw_pin}",
        "expires_at": expires_at.isoformat(),
    }


# --- 3. DOCTOR VERIFIES PIN (Brute-Force Protected + One-Time Burn) ---

@router.post("/doctor/verify-pin", response_model=DoctorSessionResponse)
def verify_consultation_pin(payload: PinVerificationRequest):
    attempts = _PIN_ATTEMPTS.get(payload.patient_id, 0)
    if attempts >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded: Maximum 3 PIN verification attempts allowed.",
        )

    pin_record = _ACTIVE_PINS.get(payload.patient_id)
    if not pin_record or pin_record["is_used"] or is_pin_expired(pin_record["expires_at"]):
        _PIN_ATTEMPTS[payload.patient_id] = attempts + 1
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Consultation PIN is invalid, expired, or already used.",
        )

    if not verify_pin_hash(payload.pin, pin_record["pin_hash"]):
        _PIN_ATTEMPTS[payload.patient_id] = attempts + 1
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect consultation PIN.",
        )

    pin_record["is_used"] = True

    scoped_token = create_Scoped_doctor_token(
        doctor_id=payload.doctor_id,
        target_patient_id=payload.patient_id,
    )

    _AUDIT_TRAIL.setdefault(payload.patient_id, []).append({
        "actor_id": payload.doctor_id,
        "actor_role": "DOCTOR",
        "action_summary": f"Doctor {payload.doctor_id} granted 30-min read-only wallet access via PIN",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return DoctorSessionResponse(
        access_token=scoped_token,
        expires_in_minutes=settings.DOCTOR_SESSION_EXPIRE_MINUTES,
        allowed_scopes=["wallet:read", "prescription:create", "first_aid:write"],
    )


# --- 4. DOCTOR AI VOICE-TO-PRESCRIPTION PARSER & CONFIRMATION ---

@router.post("/doctor/dictate-prescription", response_model=PrescriptionCreateSchema)
def dictate_prescription_draft(
    body: DictationRequest,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_doctor_scope(token_payload, "prescription:create")
    return parse_doctor_dictation_with_gemini(body.transcript)


@router.post("/doctor/patient/{patient_id}/prescriptions")
def confirm_and_assign_prescription(
    patient_id: str,
    prescription: PrescriptionCreateSchema,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_doctor_scope(token_payload, "prescription:create")
    verify_patient_resource_access(token_payload, patient_id)

    rx_record = prescription.model_dump(mode="json")
    rx_record["doctor_id"] = token_payload["sub"]
    rx_record["created_at"] = datetime.now(timezone.utc).isoformat()

    _PATIENT_PRESCRIPTIONS.setdefault(patient_id, []).append(rx_record)

    calendar_sync = None
    if prescription.next_appointment_date:
        calendar_sync = build_google_calendar_appointment_sync(
            patient_name=f"Patient {patient_id}",
            doctor_name=f"Dr. {token_payload['sub']}",
            hospital_name="Catalyst Partner Hospital",
            appointment_date=prescription.next_appointment_date,
        )

    _AUDIT_TRAIL.setdefault(patient_id, []).append({
        "actor_id": token_payload["sub"],
        "actor_role": "DOCTOR",
        "action_summary": f"Assigned {len(prescription.medications)} medication(s) for: {prescription.diagnosis_notes}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "status": "prescription_added",
        "prescription": rx_record,
        "google_calendar_sync": calendar_sync,
    }


# --- 5. ANY AUTHORIZED DOCTOR CAN CREATE OR UPDATE FIRST-AID + STORE LOCAL VOICE ---

@router.put("/doctor/patient/{patient_id}/first-aid")
def update_patient_first_aid(
    patient_id: str,
    first_aid: EmergencyFirstAidSchema,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_doctor_scope(token_payload, "first_aid:write")
    verify_patient_resource_access(token_payload, patient_id)

    doctor_id = token_payload["sub"]
    previous_record = _PATIENT_FIRST_AID.get(patient_id)

    # Pre-generate and store localized voice scripts (EN, HI, MR) for local caching
    voice_cache = build_first_aid_local_voice_cache(first_aid)

    updated_record = first_aid.model_dump(mode="json")
    updated_record["updated_by_doctor_id"] = doctor_id
    updated_record["updated_at"] = datetime.now(timezone.utc).isoformat()
    updated_record["cached_local_voice"] = voice_cache

    _PATIENT_FIRST_AID[patient_id] = updated_record

    _AUDIT_TRAIL.setdefault(patient_id, []).append({
        "actor_id": doctor_id,
        "actor_role": "DOCTOR",
        "action_summary": f"Dr. {doctor_id} updated emergency first-aid protocol ({first_aid.condition_trigger}) and refreshed local voice cache",
        "previous_state": previous_record,
        "new_state": updated_record,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "status": "first_aid_updated",
        "first_aid": updated_record,
    }


# --- 6. SMART EMERGENCY SOS (Uses Doctor's Dynamic First Aid & Stored Local Voice) ---

@router.post("/emergency/sos")
def trigger_emergency_sos(sos: SOSTriggerRequest):
    if not sos.countdown_completed:
        return {
            "status": "cancelled_within_5_sec_window",
            "dispatched": False,
        }

    # Fetch strictly what the doctor configured for this patient (no hardcoded medical steps)
    first_aid_record = _PATIENT_FIRST_AID.get(sos.patient_id)
    active_lang = _PATIENT_LANGUAGES.get(sos.patient_id, LanguageCode.MR)

    local_voice_to_play = None
    if first_aid_record and "cached_local_voice" in first_aid_record:
        local_voice_to_play = first_aid_record["cached_local_voice"].get(active_lang.value)

    maps_link = f"https://www.google.com/maps?q={sos.latitude},{sos.longitude}"

    return {
        "status": "EMERGENCY_SOS_DISPATCHED",
        "dispatched": True,
        "triggered_via": sos.triggered_via,
        "live_location_google_maps": maps_link,
        "doctor_recommended_first_aid": first_aid_record,
        "local_voice_readout": local_voice_to_play,
    }


# --- 7. VERNACULAR MEDICATION REMINDER & AUDIT LOGS ---

@router.get("/patient/{patient_id}/voice-reminder")
def get_vernacular_medication_reminder(
    patient_id: str,
    med_name: str,
    dosage: str = "1 tablet",
    meal_timing: MealTiming = MealTiming.AFTER_MEAL,
    lang: Optional[LanguageCode] = None,
):
    resolved_lang = lang or _PATIENT_LANGUAGES.get(patient_id, LanguageCode.MR)
    return generate_vernacular_voice_readout(med_name, dosage, meal_timing, resolved_lang)


@router.get("/patient/{patient_id}/audit-logs")
def get_patient_audit_logs(
    patient_id: str,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_patient_resource_access(token_payload, patient_id)
    return {"patient_id": patient_id, "audit_logs": _AUDIT_TRAIL.get(patient_id, [])}