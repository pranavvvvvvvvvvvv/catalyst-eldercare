from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.core.security import create_user_access_token
from app.main import app

client = TestClient(app)


def test_end_to_end_pin_generation_one_time_burn_and_doctor_rx_flow():
    elder_token = create_user_access_token(user_id="elder_101", role="ELDER")

    pin_res = client.post(
        "/api/v1/patient/elder_101/generate-pin",
        headers={"Authorization": f"Bearer {elder_token}"},
    )
    assert pin_res.status_code == 200
    raw_pin = pin_res.json()["consultation_pin"]

    verify_res = client.post(
        "/api/v1/doctor/verify-pin",
        json={"patient_id": "elder_101", "doctor_id": "dr_patil", "pin": raw_pin},
    )
    assert verify_res.status_code == 200
    doctor_jwt = verify_res.json()["access_token"]

    # Replaying the exact same PIN a second time must fail (One-Time Burn)
    replay_res = client.post(
        "/api/v1/doctor/verify-pin",
        json={"patient_id": "elder_101", "doctor_id": "dr_patil", "pin": raw_pin},
    )
    assert replay_res.status_code == 401

    dictate_res = client.post(
        "/api/v1/doctor/dictate-prescription",
        headers={"Authorization": f"Bearer {doctor_jwt}"},
        json={"transcript": "Hypertension checkup. Take Amlodipine 5mg morning and evening after meal."},
    )
    assert dictate_res.status_code == 200
    draft = dictate_res.json()
    assert draft["medications"][0]["morning"] is True
    assert draft["medications"][0]["evening"] is True

    next_appt = str(date.today() + timedelta(days=7))
    draft["next_appointment_date"] = next_appt
    confirm_res = client.post(
        "/api/v1/doctor/patient/elder_101/prescriptions",
        headers={"Authorization": f"Bearer {doctor_jwt}"},
        json=draft,
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["google_calendar_sync"]["calendar_provider"] == "google_calendar"


def test_pin_brute_force_rate_limit_locks_after_3_failed_attempts():
    elder_token = create_user_access_token(user_id="elder_brute", role="ELDER")
    client.post(
        "/api/v1/patient/elder_brute/generate-pin",
        headers={"Authorization": f"Bearer {elder_token}"},
    )

    for _ in range(3):
        res = client.post(
            "/api/v1/doctor/verify-pin",
            json={"patient_id": "elder_brute", "doctor_id": "dr_1", "pin": "000000"},
        )
        assert res.status_code == 401

    blocked_res = client.post(
        "/api/v1/doctor/verify-pin",
        json={"patient_id": "elder_brute", "doctor_id": "dr_1", "pin": "000000"},
    )
    assert blocked_res.status_code == 429


def test_multiple_doctors_can_update_first_aid_and_refresh_local_voice_cache():
    elder_token = create_user_access_token(user_id="elder_sos", role="ELDER")

    # Doctor 1 (Dr. Kulkarni) gets access and sets cardiac First Aid
    pin1 = client.post(
        "/api/v1/patient/elder_sos/generate-pin",
        headers={"Authorization": f"Bearer {elder_token}"},
    ).json()["consultation_pin"]
    doc1_jwt = client.post(
        "/api/v1/doctor/verify-pin",
        json={"patient_id": "elder_sos", "doctor_id": "dr_kulkarni", "pin": pin1},
    ).json()["access_token"]

    fa1_res = client.put(
        "/api/v1/doctor/patient/elder_sos/first-aid",
        headers={"Authorization": f"Bearer {doc1_jwt}"},
        json={
            "condition_trigger": "Sudden chest heaviness",
            "immediate_steps": ["Place 1 Sorbitrate 5mg tablet under the tongue."],
            "do_not_do": "Do not allow patient to walk.",
            "updated_by_doctor_id": "dr_kulkarni",
        },
    )
    assert fa1_res.status_code == 200
    assert "mr" in fa1_res.json()["first_aid"]["cached_local_voice"]

    # Later, Doctor 2 (Dr. Deshmukh) consults and updates First Aid for Severe Hypoglycemia
    pin2 = client.post(
        "/api/v1/patient/elder_sos/generate-pin",
        headers={"Authorization": f"Bearer {elder_token}"},
    ).json()["consultation_pin"]
    doc2_jwt = client.post(
        "/api/v1/doctor/verify-pin",
        json={"patient_id": "elder_sos", "doctor_id": "dr_deshmukh", "pin": pin2},
    ).json()["access_token"]

    fa2_res = client.put(
        "/api/v1/doctor/patient/elder_sos/first-aid",
        headers={"Authorization": f"Bearer {doc2_jwt}"},
        json={
            "condition_trigger": "Diabetic Dizziness / Sweating",
            "immediate_steps": ["Give 2 tablespoons of glucose powder dissolved in water immediately."],
            "do_not_do": "Do not give insulin injection during low blood sugar.",
            "updated_by_doctor_id": "dr_deshmukh",
        },
    )
    assert fa2_res.status_code == 200

    # Patient toggles language to Hindi ('hi')
    client.put(
        "/api/v1/patient/elder_sos/language",
        headers={"Authorization": f"Bearer {elder_token}"},
        json={"preferred_language": "hi"},
    )

    # Trigger SOS -> Must return Doctor 2's updated First Aid and the cached Hindi voice readout
    sos_res = client.post(
        "/api/v1/emergency/sos",
        json={
            "patient_id": "elder_sos",
            "triggered_via": "VOICE_AMBULANCE",
            "latitude": 18.6298,
            "longitude": 73.7997,
            "countdown_completed": True,
        },
    )
    assert sos_res.status_code == 200
    data = sos_res.json()
    assert data["doctor_recommended_first_aid"]["updated_by_doctor_id"] == "dr_deshmukh"
    assert "glucose" in data["doctor_recommended_first_aid"]["immediate_steps"][0]
    assert data["local_voice_readout"]["tts_locale"] == "hi-IN"


def test_vernacular_marathi_voice_readout():
    res = client.get(
        "/api/v1/patient/elder_101/voice-reminder",
        params={"med_name": "Amlodipine", "dosage": "5mg", "meal_timing": "AFTER_MEAL", "lang": "mr"},
    )
    assert res.status_code == 200
    assert res.json()["google_tts_voice"] == "mr-IN-Wavenet-A"
    assert "आजी-आजोबा" in res.json()["spoken_script"]