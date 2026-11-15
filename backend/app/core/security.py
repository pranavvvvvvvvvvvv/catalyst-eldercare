import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import bcrypt
import jwt
from fastapi import HTTPException, status
from app.core.config import settings


# --- 1. Cryptographic PIN Generation & Bcrypt Hashing ---

def generate_six_digit_pin() -> str:
    """Generates a cryptographically secure 6-digit numeric PIN."""
    return f"{secrets.randbelow(900000) + 100000}"


def hash_pin(pin: str) -> str:
    """Hashes a 6-digit PIN using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pin.encode("utf-8"), salt).decode("utf-8")


def verify_pin_hash(plain_pin: str, hashed_pin: str) -> bool:
    """Verifies a plain PIN against its bcrypt hash in constant time."""
    try:
        return bcrypt.checkpw(plain_pin.encode("utf-8"), hashed_pin.encode("utf-8"))
    except ValueError:
        return False


def is_pin_expired(expires_at: datetime) -> bool:
    """Checks if the consultation PIN has passed its 15-minute window."""
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return now >= expires_at


# --- 2. Scoped JWT Token Generation & Validation ---

DOCTOR_ALLOWED_SCOPES = ["wallet:read", "prescription:create", "first_aid:write"]


def create_user_access_token(
    user_id: str,
    role: str,
    linked_patient_ids: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Creates standard JWT for ELDER or CARETAKER roles."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": user_id,
        "role": role,
        "linked_patients": linked_patient_ids or ([user_id] if role == "ELDER" else []),
        "scopes": ["full:access"] if role == "ELDER" else ["patient:manage"],
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_Scoped_doctor_token(
    doctor_id: str,
    target_patient_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Creates a strictly time-bound (30-min), scoped JWT for a Doctor
    after scanning a Patient QR code or verifying a 6-digit PIN.
    Prevents deletion or modification of historical records.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.DOCTOR_SESSION_EXPIRE_MINUTES)
    )
    payload = {
        "sub": doctor_id,
        "role": "DOCTOR",
        "target_patient_id": target_patient_id,
        "scopes": DOCTOR_ALLOWED_SCOPES,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict:
    """Decodes and validates a JWT token, raising 401 on expiry or tampering."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired. Please re-authenticate.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )


# --- 3. BOLA (Broken Object-Level Authorization) & Scope Guards ---

def verify_patient_resource_access(token_payload: Dict, requested_patient_id: str) -> bool:
    """
    Prevents IDOR/BOLA attacks by ensuring the authenticated Elder, Caretaker,
    or temporary Doctor session is explicitly authorized for requested_patient_id.
    """
    role = token_payload.get("role")

    if role == "ELDER":
        if token_payload.get("sub") == requested_patient_id:
            return True
    elif role == "CARETAKER":
        if requested_patient_id in token_payload.get("linked_patients", []):
            return True
    elif role == "DOCTOR":
        if token_payload.get("target_patient_id") == requested_patient_id:
            return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="BOLA Protection: You do not have permission to access this patient's records.",
    )


def verify_doctor_scope(token_payload: Dict, required_scope: str) -> bool:
    """Ensures a doctor session only executes permitted append/read actions."""
    if token_payload.get("role") != "DOCTOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only verified doctors can perform this action.",
        )
    scopes = token_payload.get("scopes", [])
    if required_scope not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient scope. Required: {required_scope}",
        )
    return True