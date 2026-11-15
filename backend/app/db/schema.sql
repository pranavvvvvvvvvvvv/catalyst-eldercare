-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Users Table (Elders, Caretakers, Doctors)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role VARCHAR(20) NOT NULL CHECK (role IN ('ELDER', 'CARETAKER', 'DOCTOR')),
    name VARCHAR(120) NOT NULL,
    mobile VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    hospital_name VARCHAR(200),
    medical_reg_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Elderly Patient Medical Profile & Custom Doctor First-Aid Protocol
CREATE TABLE patient_profiles (
    patient_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    chronic_disorders TEXT[] DEFAULT '{}',
    blood_group VARCHAR(10),
    preferred_language VARCHAR(5) DEFAULT 'en' CHECK (preferred_language IN ('en', 'hi', 'mr')),
    emergency_first_aid JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Caretaker-to-Patient Authorization Links (Used for BOLA Checks)
CREATE TABLE caretaker_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    caretaker_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    can_edit_schedule BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(patient_id, caretaker_id)
);

-- 4. Time-Bound Consultation PIN / QR Passes (15-min TTL, One-Time Burn)
CREATE TABLE access_passes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pin_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Digital Health Wallet Documents (Private Bucket Paths)
CREATE TABLE wallet_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type VARCHAR(50) NOT NULL,
    uploaded_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Prescriptions & Longitudinal Diagnosis History (Append-Only for Doctors)
CREATE TABLE prescriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES users(id),
    diagnosis_notes TEXT NOT NULL,
    medications JSONB NOT NULL, -- Array of morning/afternoon/evening/meal_timing items
    next_appointment_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Immutable Security Audit Logs (Append-Only)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    actor_id UUID NOT NULL REFERENCES users(id),
    actor_role VARCHAR(20) NOT NULL,
    action_summary VARCHAR(255) NOT NULL,
    previous_state JSONB,
    new_state JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS) across all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE caretaker_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_passes ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallet_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE prescriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Database Trigger: Block UPDATE or DELETE on audit_logs (Strict Immutability)
CREATE OR REPLACE FUNCTION prevent_audit_log_tampering()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Security Policy Violation: Audit logs are strictly append-only and cannot be modified or deleted.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_immutable_audit_logs
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_tampering();