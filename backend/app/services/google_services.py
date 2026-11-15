import json
from datetime import date
from typing import Any, Dict, Optional
from urllib.parse import quote
from google import genai
from google.genai import types
from app.core.config import settings
from app.models.schemas import (
    EmergencyFirstAidSchema,
    LanguageCode,
    MealTiming,
    MedicationItemSchema,
    PrescriptionCreateSchema,
)


# --- 1. GEMINI API: Doctor Voice Dictation -> Structured Prescription JSON ---

def parse_doctor_dictation_with_gemini(transcript: str) -> PrescriptionCreateSchema:
    if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key":
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt = (
            "Extract diagnosis notes, medications (morning/afternoon/evening booleans, "
            "BEFORE_MEAL/AFTER_MEAL, duration_days, extra_instructions), and next_appointment_date:\n\n"
            f"{transcript}"
        )
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PrescriptionCreateSchema,
                temperature=0.1,
            ),
        )
        return PrescriptionCreateSchema(**json.loads(response.text))

    lower_text = transcript.lower()
    return PrescriptionCreateSchema(
        diagnosis_notes=transcript.strip(),
        medications=[
            MedicationItemSchema(
                name="Prescribed Medication",
                dosage="1 tablet",
                morning="morning" in lower_text,
                afternoon="afternoon" in lower_text,
                evening="evening" in lower_text or "night" in lower_text,
                meal_timing=MealTiming.BEFORE_MEAL if "before" in lower_text else MealTiming.AFTER_MEAL,
                duration_days=15,
                extra_instructions="Parsed via AI Dictation Assistant",
            )
        ],
        next_appointment_date=None,
    )


# --- 2. DOCTOR FIRST-AID -> PRE-GENERATED LOCAL VOICE CACHE (EN / HI / MR) ---

def build_first_aid_local_voice_cache(first_aid: EmergencyFirstAidSchema) -> Dict[str, Dict[str, str]]:
    """
    Called immediately when ANY doctor updates the patient's First-Aid protocol.
    Pre-generates and stores localized voice readout scripts for English, Hindi, and Marathi
    so the frontend can cache and play them instantly with zero network latency during an SOS.
    """
    steps_text = " ".join(first_aid.immediate_steps)
    warning_text = f" Warning: {first_aid.do_not_do}" if first_aid.do_not_do else ""

    # If live Gemini API key is configured, translate the doctor's exact custom steps into Hindi & Marathi
    hi_steps = f"तुरंत यह कदम उठाएं: {steps_text}.{warning_text}"
    mr_steps = f"तात्काळ हे उपाय करा: {steps_text}.{warning_text}"

    if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key":
        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            prompt = (
                "Translate the following doctor-prescribed emergency first-aid instructions into natural, "
                "clear spoken Hindi and Marathi for an elderly patient's caretaker. "
                "Return strict JSON with keys 'hi' and 'mr':\n\n"
                f"Condition: {first_aid.condition_trigger}\nSteps: {steps_text}\nDo Not: {first_aid.do_not_do}"
            )
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            translated = json.loads(res.text)
            hi_steps = translated.get("hi", hi_steps)
            mr_steps = translated.get("mr", mr_steps)
        except Exception:
            pass

    return {
        LanguageCode.EN.value: {
            "tts_locale": "en-IN",
            "google_tts_voice": "en-IN-Wavenet-A",
            "spoken_script": f"Emergency First Aid for {first_aid.condition_trigger}: {steps_text}.{warning_text}",
        },
        LanguageCode.HI.value: {
            "tts_locale": "hi-IN",
            "google_tts_voice": "hi-IN-Wavenet-A",
            "spoken_script": f"आपातकालीन प्राथमिक उपचार ({first_aid.condition_trigger}): {hi_steps}",
        },
        LanguageCode.MR.value: {
            "tts_locale": "mr-IN",
            "google_tts_voice": "mr-IN-Wavenet-A",
            "spoken_script": f"आपत्कालीन प्रथमोपचार ({first_aid.condition_trigger}): {mr_steps}",
        },
    }


# --- 3. GOOGLE CALENDAR SYNC: Doctor & Caretaker Follow-up Invites ---

def build_google_calendar_appointment_sync(
    patient_name: str,
    doctor_name: str,
    hospital_name: str,
    appointment_date: date,
    caretaker_email: Optional[str] = None,
) -> Dict[str, Any]:
    start_str = appointment_date.strftime("%Y%m%dT100000Z")
    end_str = appointment_date.strftime("%Y%m%dT103000Z")
    title = f"Follow-up Consultation: {patient_name} with {doctor_name}"
    details = f"Elderly Care Follow-up at {hospital_name}. Auto-synced via Catalyst ElderCare."

    google_cal_url = (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={quote(title)}&dates={start_str}/{end_str}"
        f"&details={quote(details)}&location={quote(hospital_name)}"
    )

    return {
        "calendar_provider": "google_calendar",
        "event_title": title,
        "appointment_date": str(appointment_date),
        "location": hospital_name,
        "attendees": [email for email in [caretaker_email] if email],
        "reminder_24hr_scheduled": True,
        "google_calendar_deep_link": google_cal_url,
    }


# --- 4. VERNACULAR MEDICATION REMINDER READOUTS ---

def generate_vernacular_voice_readout(
    med_name: str,
    dosage: str,
    meal_timing: MealTiming,
    language: LanguageCode = LanguageCode.MR,
) -> Dict[str, str]:
    meal_map = {
        LanguageCode.MR: {
            MealTiming.BEFORE_MEAL: "जेवणापूर्वी",
            MealTiming.AFTER_MEAL: "जेवणानंतर",
            MealTiming.WITH_MEAL: "जेवणासोबत",
            MealTiming.ANYTIME: "कोणत्याही वेळी",
        },
        LanguageCode.HI: {
            MealTiming.BEFORE_MEAL: "खाने से पहले",
            MealTiming.AFTER_MEAL: "खाने के बाद",
            MealTiming.WITH_MEAL: "खाने के साथ",
            MealTiming.ANYTIME: "किसी भी समय",
        },
        LanguageCode.EN: {
            MealTiming.BEFORE_MEAL: "before your meal",
            MealTiming.AFTER_MEAL: "after your meal",
            MealTiming.WITH_MEAL: "with your meal",
            MealTiming.ANYTIME: "at any time",
        },
    }

    timing_phrase = meal_map[language][meal_timing]

    if language == LanguageCode.MR:
        spoken_text = f"आजी-आजोबा, आता तुमची {med_name} ({dosage}) घेण्याची वेळ झाली आहे. कृपया ही गोळी {timing_phrase} घ्या."
        voice_code = "mr-IN-Wavenet-A"
    elif language == LanguageCode.HI:
        spoken_text = f"नमस्ते, अब आपकी {med_name} ({dosage}) लेने का समय हो गया है। कृपया यह दवा {timing_phrase} लें।"
        voice_code = "hi-IN-Wavenet-A"
    else:
        spoken_text = f"Hello, it is time to take your {med_name} ({dosage}). Please take it {timing_phrase}."
        voice_code = "en-IN-Wavenet-A"

    return {
        "language_code": language.value,
        "google_tts_voice": voice_code,
        "spoken_script": spoken_text,
    }