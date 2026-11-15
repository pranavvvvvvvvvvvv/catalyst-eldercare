from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    ELDER = "ELDER"
    CARETAKER = "CARETAKER"
    DOCTOR = "DOCTOR"


class MealTiming(str, Enum):
    BEFORE_MEAL = "BEFORE_MEAL"
    AFTER_MEAL = "AFTER_MEAL"
    WITH_MEAL = "WITH_MEAL"
    ANYTIME = "ANYTIME"


class LanguageCode(str, Enum):
    EN = "en"
    HI = "hi"
    MR = "mr"


# --- Auth & PIN Access Schemas ---

class PinVerificationRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, description="Target elderly patient UUID")
    doctor_id: str = Field(..., min_length=1, description="Verifying doctor UUID")
    pin: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit numeric consultation PIN",
    )


class DoctorSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    allowed_scopes: List[str]


# --- Medication & Gemini Structured Prescription Schemas ---

class MedicationItemSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=120, description="Medicine or lotion name")
    dosage: str = Field(..., min_length=1, max_length=60, description="e.g., 5mg, 1 tablet, Apply thin layer")
    morning: bool = Field(default=False)
    afternoon: bool = Field(default=False)
    evening: bool = Field(default=False)
    meal_timing: MealTiming = Field(default=MealTiming.AFTER_MEAL)
    duration_days: int = Field(..., ge=1, le=365, description="Course duration in days")
    extra_instructions: Optional[str] = Field(default=None, max_length=300)


class PrescriptionCreateSchema(BaseModel):
    """Used both for Gemini Structured Output parsing and Doctor confirmation."""
    diagnosis_notes: str = Field(..., min_length=3, max_length=1000)
    medications: List[MedicationItemSchema] = Field(..., min_length=1)
    next_appointment_date: Optional[date] = None


# --- Doctor-Recommended Emergency First Aid & SOS Schemas ---

class EmergencyFirstAidSchema(BaseModel):
    condition_trigger: str = Field(..., min_length=3, max_length=200, description="e.g., Severe chest pain or dizziness")
    immediate_steps: List[str] = Field(..., min_length=1, description="Ordered first-aid steps before ambulance arrives")
    do_not_do: Optional[str] = Field(default=None, max_length=300, description="Critical warnings")
    updated_by_doctor_id: str


class SOSTriggerRequest(BaseModel):
    patient_id: str
    triggered_via: str = Field(..., pattern=r"^(BUTTON|VOICE_AMBULANCE)$")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    countdown_completed: bool = Field(
        ...,
        description="Must be True (confirming the 5-second accidental cancel window passed)",
    )


# --- Immutable Audit Log Schema ---

class AuditLogCreateSchema(BaseModel):
    patient_id: str
    actor_id: str
    actor_role: UserRole
    action_summary: str = Field(..., min_length=5, max_length=255)
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)