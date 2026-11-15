import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.file_validator import validate_medical_file_upload
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
from app.db.supabase_client import get_supabase_client
from app.models.schemas import (
    DoctorSessionResponse,
    EmergencyFirstAidSchema,
    LanguageCode,
    MealTiming,
    PinVerificationRequest,
    PrescriptionCreateSchema,
    SOSTriggerRequest,
)
from app.services.email_service import send_notification_email
from app.services.google_services import (
    build_first_aid_local_voice_cache,
    build_google_calendar_appointment_sync,
    generate_vernacular_voice_readout,
    parse_doctor_dictation_with_gemini,
)

router = APIRouter(prefix="/api/v1")

# Synchronized In-Memory + Supabase Cache
_ACTIVE_PINS: Dict[str, Dict[str, Any]] = {}
_PIN_ATTEMPTS: Dict[str, int] = {}
_PATIENT_FIRST_AID: Dict[str, Dict[str, Any]] = {}
_PATIENT_PRESCRIPTIONS: Dict[str, list] = {}
_PATIENT_LANGUAGES: Dict[str, LanguageCode] = {}
_PATIENT_PROFILES: Dict[str, Dict[str, Any]] = {}
_PATIENT_WALLET: Dict[str, list] = {}
_PATIENT_CARETAKERS: Dict[str, list] = {}
_PATIENT_APPOINTMENTS: Dict[str, list] = {}
_AUDIT_TRAIL: Dict[str, list] = {}


def _log_audit(patient_id: str, actor_id: str, actor_role: str, summary: str):
    entry = {
        "patient_id": patient_id,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action_summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _AUDIT_TRAIL.setdefault(patient_id, []).insert(0, entry)
    sb = get_supabase_client()
    if sb:
        try:
            sb.table("audit_logs").insert(entry).execute()
        except Exception as e:
            print("Supabase audit insert warning:", e)


def get_current_token_payload(authorization: str = Header(...)) -> Dict[str, Any]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = authorization.replace("Bearer ", "", 1).strip()
    return decode_access_token(token)


class DictationRequest(BaseModel):
    transcript: str = Field(..., min_length=5, max_length=2000)


class LanguageToggleRequest(BaseModel):
    preferred_language: LanguageCode


class CaretakerLinkRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    relation: str = Field(..., min_length=2, max_length=50)
    email: str = Field(..., min_length=5, max_length=120)
    phone: str = Field(default="", max_length=20)


class AppointmentCreateRequest(BaseModel):
    doctor_name: str = Field(..., min_length=2, max_length=100)
    hospital_name: str = Field(..., min_length=2, max_length=150)
    appointment_date: str = Field(..., description="YYYY-MM-DD")
    notes: str = Field(default="Routine Checkup", max_length=300)


# --- 1. DEMO TOKEN & UNIFIED DASHBOARD LOADER (Reads from Supabase if connected) ---

@router.get("/demo/token/{role}/{user_id}")
def get_demo_token(role: str, user_id: str, linked_patient_id: str = "elder_101"):
    target = user_id if role.upper() == "ELDER" else linked_patient_id
    token = create_user_access_token(
        user_id=user_id,
        role=role.upper(),
        linked_patient_ids=[target],
    )
    return {"access_token": token, "role": role.upper(), "user_id": user_id}


@router.get("/patient/{patient_id}/dashboard")
def get_patient_dashboard_summary(patient_id: str):
    sb = get_supabase_client()
    if sb:
        try:
            rec = sb.table("patient_records").select("*").eq("patient_id", patient_id).execute()
            if rec.data:
                row = rec.data[0]
                _PATIENT_PROFILES[patient_id] = {
                    "blood_group": row.get("blood_group", ""),
                    "chronic_disorders": row.get("chronic_disorders", ""),
                }
                if row.get("first_aid"):
                    _PATIENT_FIRST_AID[patient_id] = row["first_aid"]

            w_res = sb.table("wallet_documents").select("*").eq("patient_id", patient_id).execute()
            if w_res.data is not None:
                for doc in w_res.data:
                    storage_path = doc.get("storage_path")
                    if storage_path:
                        try:
                            # Robust fallback check: ensure path is clean for Supabase storage lookup
                            clean_path = storage_path.strip("/")
                            signed_res = sb.storage.from_("health-wallet").create_signed_url(clean_path, 3600)
                            doc["preview_url"] = signed_res.get("signedURL") or signed_res.get("signedUrl")
                        except Exception as e:
                            print(f"Supabase signed URL error for '{storage_path}': {e}", flush=True)
                            doc["preview_url"] = None
                _PATIENT_WALLET[patient_id] = w_res.data

            c_res = sb.table("patient_caretakers").select("*").eq("patient_id", patient_id).execute()
            if c_res.data is not None:
                _PATIENT_CARETAKERS[patient_id] = c_res.data

            a_res = sb.table("patient_appointments").select("*").eq("patient_id", patient_id).execute()
            if a_res.data is not None:
                _PATIENT_APPOINTMENTS[patient_id] = a_res.data

            p_res = sb.table("patient_prescriptions").select("*").eq("patient_id", patient_id).execute()
            if p_res.data is not None:
                _PATIENT_PRESCRIPTIONS[patient_id] = p_res.data

            l_res = sb.table("audit_logs").select("*").eq("patient_id", patient_id).order("id", desc=True).execute()
            if l_res.data is not None:
                _AUDIT_TRAIL[patient_id] = l_res.data
        except Exception as e:
            print("Supabase dashboard fetch warning:", e)

    return {
        "patient_id": patient_id,
        "preferred_language": _PATIENT_LANGUAGES.get(patient_id, LanguageCode.MR).value,
        "profile": _PATIENT_PROFILES.get(patient_id, {"blood_group": "O+", "chronic_disorders": ""}),
        "wallet": _PATIENT_WALLET.get(patient_id, []),
        "caretakers": _PATIENT_CARETAKERS.get(patient_id, []),
        "appointments": _PATIENT_APPOINTMENTS.get(patient_id, []),
        "prescriptions": _PATIENT_PRESCRIPTIONS.get(patient_id, []),
        "first_aid": _PATIENT_FIRST_AID.get(patient_id),
        "audit_logs": _AUDIT_TRAIL.get(patient_id, []),
    }


# --- 2. LANGUAGE TOGGLE & PIN GENERATION ---

@router.put("/patient/{patient_id}/language")
def toggle_patient_language(
    patient_id: str,
    body: LanguageToggleRequest,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_patient_resource_access(token_payload, patient_id)
    _PATIENT_LANGUAGES[patient_id] = body.preferred_language
    first_aid_record = _PATIENT_FIRST_AID.get(patient_id)
    local_first_aid_voice = None
    if first_aid_record and "cached_local_voice" in first_aid_record:
        local_first_aid_voice = first_aid_record["cached_local_voice"].get(body.preferred_language.value)

    return {
        "patient_id": patient_id,
        "preferred_language": body.preferred_language.value,
        "cached_first_aid_voice": local_first_aid_voice,
    }


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
    _log_audit(patient_id, token_payload["sub"], "ELDER", "Generated 15-minute one-time Doctor Consent PIN")

    return {
        "patient_id": patient_id,
        "consultation_pin": raw_pin,
        "qr_payload": f"eldercare://verify?patient_id={patient_id}&pin={raw_pin}",
        "expires_at": expires_at.isoformat(),
    }


# --- 3. DOCTOR PIN VERIFICATION, DICTATION, PRESCRIPTIONS & FIRST AID ---

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
    _log_audit(
        payload.patient_id,
        payload.doctor_id,
        "DOCTOR",
        f"Doctor {payload.doctor_id} unlocked 30-min consultation access via PIN",
    )

    return DoctorSessionResponse(
        access_token=scoped_token,
        expires_in_minutes=settings.DOCTOR_SESSION_EXPIRE_MINUTES,
        allowed_scopes=["wallet:read", "prescription:create", "first_aid:write"],
    )


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
    background_tasks: BackgroundTasks,
    caretaker_email: Optional[str] = None,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_doctor_scope(token_payload, "prescription:create")
    verify_patient_resource_access(token_payload, patient_id)

    rx_record = prescription.model_dump(mode="json")
    rx_record["patient_id"] = patient_id
    rx_record["doctor_id"] = token_payload["sub"]
    rx_record["is_completed"] = False
    rx_record["created_at"] = datetime.now(timezone.utc).isoformat()

    _PATIENT_PRESCRIPTIONS.setdefault(patient_id, []).append(rx_record)

    sb = get_supabase_client()
    if sb:
        try:
            sb.table("patient_prescriptions").insert({
                "patient_id": patient_id,
                "doctor_id": rx_record["doctor_id"],
                "diagnosis_notes": rx_record["diagnosis_notes"],
                "medications": rx_record["medications"],
                "next_appointment_date": str(rx_record.get("next_appointment_date") or ""),
                "is_completed": False,
                "created_at": rx_record["created_at"],
            }).execute()
        except Exception as e:
            print("Supabase prescription insert warning:", e)

    calendar_sync = None
    if prescription.next_appointment_date:
        calendar_sync = build_google_calendar_appointment_sync(
            patient_name=f"Patient {patient_id}",
            doctor_name=f"Dr. {token_payload['sub']}",
            hospital_name="Catalyst Partner Hospital",
            appointment_date=prescription.next_appointment_date,
            caretaker_email=caretaker_email,
        )

    _log_audit(
        patient_id,
        token_payload["sub"],
        "DOCTOR",
        f"Assigned {len(prescription.medications)} medication(s) for: {prescription.diagnosis_notes}",
    )

    if caretaker_email:
        background_tasks.add_task(
            send_notification_email,
            to_email=caretaker_email,
            subject=f"New Prescription Added for {patient_id}",
            body_text=f"Dr. {token_payload['sub']} added a course for {prescription.diagnosis_notes}.",
        )

    return {
        "status": "prescription_added",
        "prescription": rx_record,
        "google_calendar_sync": calendar_sync,
    }


@router.put("/doctor/patient/{patient_id}/first-aid")
def update_patient_first_aid(
    patient_id: str,
    first_aid: EmergencyFirstAidSchema,
    background_tasks: BackgroundTasks,
    caretaker_email: Optional[str] = None,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_doctor_scope(token_payload, "first_aid:write")
    verify_patient_resource_access(token_payload, patient_id)

    doctor_id = token_payload["sub"]
    voice_cache = build_first_aid_local_voice_cache(first_aid)

    updated_record = first_aid.model_dump(mode="json")
    updated_record["updated_by_doctor_id"] = doctor_id
    updated_record["updated_at"] = datetime.now(timezone.utc).isoformat()
    updated_record["cached_local_voice"] = voice_cache

    _PATIENT_FIRST_AID[patient_id] = updated_record

    sb = get_supabase_client()
    if sb:
        try:
            sb.table("patient_records").upsert({
                "patient_id": patient_id,
                "first_aid": updated_record,
            }).execute()
        except Exception as e:
            print("Supabase first-aid upsert warning:", e)

    _log_audit(
        patient_id,
        doctor_id,
        "DOCTOR",
        f"Dr. {doctor_id} updated emergency first-aid protocol ({first_aid.condition_trigger}) and cached local voice",
    )

    if caretaker_email:
        background_tasks.add_task(
            send_notification_email,
            to_email=caretaker_email,
            subject=f"Emergency First Aid Updated for {patient_id}",
            body_text=f"Dr. {doctor_id} updated First Aid for {first_aid.condition_trigger}.",
        )

    return {"status": "first_aid_updated", "first_aid": updated_record}


# --- 4. SMART EMERGENCY SOS & VOICE REMINDERS ---

@router.post("/emergency/sos")
def trigger_emergency_sos(sos: SOSTriggerRequest):
    if not sos.countdown_completed:
        return {"status": "cancelled_within_5_sec_window", "dispatched": False}

    first_aid_record = _PATIENT_FIRST_AID.get(sos.patient_id)
    active_lang = _PATIENT_LANGUAGES.get(sos.patient_id, LanguageCode.MR)

    local_voice_to_play = None
    if first_aid_record and "cached_local_voice" in first_aid_record:
        local_voice_to_play = first_aid_record["cached_local_voice"].get(active_lang.value)

    maps_link = f"https://www.google.com/maps?q={sos.latitude},{sos.longitude}"
    _log_audit(sos.patient_id, sos.patient_id, "ELDER", f"Triggered Emergency SOS via {sos.triggered_via}")

    return {
        "status": "EMERGENCY_SOS_DISPATCHED",
        "dispatched": True,
        "triggered_via": sos.triggered_via,
        "live_location_google_maps": maps_link,
        "doctor_recommended_first_aid": first_aid_record,
        "local_voice_readout": local_voice_to_play,
    }


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


# --- 5. PROFILE, SUPABASE WALLET UPLOAD, CARETAKERS & APPOINTMENTS ---

@router.get("/patient/{patient_id}/profile")
def get_patient_profile(
    patient_id: str,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_patient_resource_access(token_payload, patient_id)
    profile = _PATIENT_PROFILES.get(patient_id, {"blood_group": "O+", "chronic_disorders": ""})
    wallet = _PATIENT_WALLET.get(patient_id, [])
    return {"profile": profile, "wallet": wallet}


@router.put("/patient/{patient_id}/profile")
def update_patient_profile(
    patient_id: str,
    profile_data: Dict[str, Any],
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_patient_resource_access(token_payload, patient_id)
    _PATIENT_PROFILES[patient_id] = profile_data

    sb = get_supabase_client()
    if sb:
        try:
            sb.table("patient_records").upsert({
                "patient_id": patient_id,
                "blood_group": profile_data.get("blood_group", ""),
                "chronic_disorders": profile_data.get("chronic_disorders", ""),
            }).execute()
        except Exception as e:
            print("Supabase profile upsert warning:", e)

    _log_audit(patient_id, token_payload["sub"], token_payload["role"], "Updated medical profile (Blood Group & Chronic Conditions)")
    return {"status": "success", "profile": profile_data}


@router.post("/patient/{patient_id}/wallet/upload")
async def upload_wallet_document(
    patient_id: str,
    file: UploadFile = File(...),
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_patient_resource_access(token_payload, patient_id)
    file_bytes = await file.read()
    detected_mime = validate_medical_file_upload(file_bytes, file.content_type or "application/octet-stream")

    ext = "pdf" if detected_mime == "application/pdf" else "jpg"
    storage_path = f"{patient_id}/{uuid.uuid4().hex}.{ext}"
    signed_preview_url = None

    sb = None
    try:
        sb = get_supabase_client()
    except Exception as e:
        print(f"Supabase client initialization error: {e}", flush=True)

    if sb:
        try:
            sb.storage.from_("health-wallet").upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": detected_mime, "upsert": "false"},
            )
            signed_res = sb.storage.from_("health-wallet").create_signed_url(storage_path, 3600)
            signed_preview_url = signed_res.get("signedURL") or signed_res.get("signedUrl")
        except Exception as e:
            print(f"Supabase storage upload error: {e}", flush=True)

    file_record = {
        "patient_id": patient_id,
        "uploaded_by": token_payload["sub"],
        "title": file.filename,
        "mime_type": detected_mime,
        "storage_path": storage_path,
        "preview_url": signed_preview_url,
        "file_size_bytes": len(file_bytes),
        "uploaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "status": "Verified & Stored in Supabase" if signed_preview_url else "Verified (Magic-Byte Passed)",
    }
    _PATIENT_WALLET.setdefault(patient_id, []).append(file_record)

    if sb:
        try:
            sb.table("wallet_documents").insert(file_record).execute()
        except Exception as e:
            print(f"Supabase wallet_documents table insert error: {e}", flush=True)

    _log_audit(patient_id, token_payload["sub"], token_payload["role"], f"Uploaded medical file '{file.filename}' to Health Wallet")
    return {"status": "uploaded", "file": file_record}


@router.post("/patient/{patient_id}/caretakers")
def add_family_caretaker(
    patient_id: str,
    caretaker: CaretakerLinkRequest,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_patient_resource_access(token_payload, patient_id)
    record = {
        "patient_id": patient_id,
        "name": caretaker.name,
        "relation": caretaker.relation,
        "email": caretaker.email.strip().lower(),
        "granted_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    }
    _PATIENT_CARETAKERS.setdefault(patient_id, []).append(record)

    sb = get_supabase_client()
    if sb:
        try:
            sb.table("patient_caretakers").insert(record).execute()
        except Exception as e:
            print("Supabase caretaker insert warning:", e)

    _log_audit(patient_id, token_payload["sub"], token_payload["role"], f"Granted Caretaker Portal access to {caretaker.name} ({caretaker.email})")
    return {"status": "caretaker_linked", "caretaker": record}


@router.get("/caretaker/patients")
def get_linked_patients_for_caretaker(email: str):
    normalized_email = email.strip().lower()
    linked_patients = []
    seen_pids = set()

    sb = get_supabase_client()
    if sb:
        try:
            res = sb.table("patient_caretakers").select("*").eq("email", normalized_email).execute()
            for ct in res.data or []:
                pid = ct["patient_id"]
                if pid not in seen_pids:
                    seen_pids.add(pid)
                    linked_patients.append({
                        "patient_id": pid,
                        "relation": ct.get("relation", "Family"),
                        "caretaker_name": ct.get("name", ""),
                        "granted_at": ct.get("granted_at", ""),
                    })
        except Exception as e:
            print("Supabase caretaker lookup warning:", e)

    for pid, ct_list in _PATIENT_CARETAKERS.items():
        for ct in ct_list:
            if ct.get("email", "").strip().lower() == normalized_email and pid not in seen_pids:
                seen_pids.add(pid)
                linked_patients.append({
                    "patient_id": pid,
                    "relation": ct.get("relation", "Family"),
                    "caretaker_name": ct.get("name", ""),
                    "granted_at": ct.get("granted_at", ""),
                })

    return {"caretaker_email": normalized_email, "linked_patients": linked_patients}


@router.post("/patient/{patient_id}/appointments")
def add_patient_appointment(
    patient_id: str,
    appt: AppointmentCreateRequest,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_patient_resource_access(token_payload, patient_id)
    parsed_date = datetime.strptime(appt.appointment_date, "%Y-%m-%d").date()
    cal_sync = build_google_calendar_appointment_sync(
        patient_name=f"Patient {patient_id}",
        doctor_name=appt.doctor_name,
        hospital_name=appt.hospital_name,
        appointment_date=parsed_date,
    )
    record = {
        "patient_id": patient_id,
        "doctor_name": appt.doctor_name,
        "hospital_name": appt.hospital_name,
        "appointment_date": appt.appointment_date,
        "notes": appt.notes,
        "google_calendar_deep_link": cal_sync["google_calendar_deep_link"],
    }
    _PATIENT_APPOINTMENTS.setdefault(patient_id, []).append(record)

    sb = get_supabase_client()
    if sb:
        try:
            sb.table("patient_appointments").insert(record).execute()
        except Exception as e:
            print("Supabase appointment insert warning:", e)

    _log_audit(patient_id, token_payload["sub"], token_payload["role"], f"Scheduled appointment with {appt.doctor_name} on {appt.appointment_date}")
    return {"status": "appointment_scheduled", "appointment": record}


@router.put("/patient/{patient_id}/prescriptions/{rx_index}/complete")
def mark_prescription_completed(
    patient_id: str,
    rx_index: int,
    token_payload: Dict = Depends(get_current_token_payload),
):
    verify_patient_resource_access(token_payload, patient_id)
    rx_list = _PATIENT_PRESCRIPTIONS.get(patient_id, [])
    if 0 <= rx_index < len(rx_list):
        rx_list[rx_index]["is_completed"] = True
        _log_audit(patient_id, token_payload["sub"], token_payload["role"], f"Marked course '{rx_list[rx_index].get('diagnosis_notes')}' as completed")
    return {"status": "completed"}


class UserSyncRequest(BaseModel):
    user_id: str
    name: str
    email: str
    role: str # "ELDER", "DOCTOR", or "CARETAKER"


@router.post("/auth/sync-user")
def sync_user_to_supabase(payload: UserSyncRequest):
    sb = get_supabase_client()
    if not sb:
        return {"status": "success", "mode": "local_fallback"}

    try:
        sb.table("users").upsert({
            "user_id": payload.user_id,
            "name": payload.name,
            "email": payload.email,
            "role": payload.role,
        }, on_conflict="user_id").execute()

        if payload.role == "ELDER":
            sb.table("patient_records").upsert({
                "patient_id": payload.user_id,
                "preferred_language": "mr",
                "blood_group": "O+",
                "chronic_disorders": "",
            }, on_conflict="patient_id").execute()

        return {"status": "synced_to_supabase", "user_id": payload.user_id}
    except Exception as e:
        print("Supabase user sync error:", e)
        return {"status": "error", "detail": str(e)}