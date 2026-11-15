import React, { useState, useRef } from "react";
import { GoogleOAuthProvider } from "@react-oauth/google";
import { api, speakText, UI_TRANSLATIONS } from "./services/api";

import LoginScreen from "./components/LoginScreen";
import Header from "./components/Header";
import EmergencyBar from "./components/EmergencyBar";
import SeniorProtocol from "./components/SeniorProtocol";
import DoctorProtocol from "./components/DoctorProtocol";
import CaretakerProtocol from "./components/CaretakerProtocol";

const GOOGLE_CLIENT_ID =
  import.meta.env.VITE_GOOGLE_CLIENT_ID ||
  "312916056842-ffjtbt4l3506k8vgg8eq3olfv0c40njg.apps.googleusercontent.com";

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [lang, setLang] = useState("mr");
  const [highContrast, setHighContrast] = useState(true);
  const [voiceCommandsOn, setVoiceCommandsOn] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  const [patientId] = useState("elder_101");
  const [elderToken, setElderToken] = useState("");
  const [generatedPin, setGeneratedPin] = useState(null);

  // Patient Data Stores
  const [patientProfile, setPatientProfile] = useState({});
  const [patientWallet, setPatientWallet] = useState([]);
  const [caretakers, setCaretakers] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [prescriptions, setPrescriptions] = useState([]);
  const [firstAid, setFirstAid] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);

  // Doctor & Caretaker Target Patient Session State
  const [doctorToken, setDoctorToken] = useState("");
  const [targetPatientId, setTargetPatientId] = useState("elder_101");
  const [pinInput, setPinInput] = useState("");
  const [caretakerEmail, setCaretakerEmail] = useState("caretaker@example.com");
  const [rxDraft, setRxDraft] = useState(null);
  const [calendarSyncInfo, setCalendarSyncInfo] = useState(null);

  // Emergency SOS State
  const [sosCountdown, setSosCountdown] = useState(null);
  const [sosDispatchedData, setSosDispatchedData] = useState(null);
  const countdownTimerRef = useRef(null);

  const t = UI_TRANSLATIONS[lang];

  const refreshDashboard = async (pId = patientId) => {
    try {
      const res = await api.get(`/patient/${pId}/dashboard`);
      setPatientProfile(res.data.profile || {});
      setPatientWallet(res.data.wallet || []);
      setCaretakers(res.data.caretakers || []);
      setAppointments(res.data.appointments || []);
      setPrescriptions(res.data.prescriptions || []);
      setFirstAid(res.data.first_aid || null);
      setAuditLogs(res.data.audit_logs || []);
    } catch (e) {
      console.error("Dashboard refresh failed", e);
    }
  };

  const handleUserLogin = async (userData) => {
    setCurrentUser(userData);
    setStatusMsg("");

    // Automatically sync/save user to Supabase on login
    try {
      await api.post("/auth/sync-user", {
        user_id: userData.role === "ELDER" ? patientId : userData.email.split("@")[0],
        name: userData.name,
        email: userData.email,
        role: userData.role,
      });
    } catch (err) {
      console.error("Supabase user sync warning:", err);
    }

    if (userData.role === "ELDER") {
      setCaretakerEmail(userData.email);
      const tokRes = await api.get(`/demo/token/ELDER/${patientId}`);
      setElderToken(tokRes.data.access_token);
      await refreshDashboard(patientId);
    } else if (userData.role === "CARETAKER") {
      setTargetPatientId("");
      setElderToken("");
      setPrescriptions([]);
      setAppointments([]);
      setFirstAid(null);
      setAuditLogs([]);
    } else if (userData.role === "DOCTOR") {
      setDoctorToken("");
      setPrescriptions([]);
      setFirstAid(null);
      setAuditLogs([]);
    }
  };

  const handleLanguageChange = async (newLang) => {
    setLang(newLang);
    if (!elderToken) return;
    await api.put(
      `/patient/${patientId}/language`,
      { preferred_language: newLang },
      { headers: { Authorization: `Bearer ${elderToken}` } }
    );
  };

  const toggleVoiceCommandListener = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setStatusMsg("Web Speech API not supported in this browser.");
      return;
    }
    if (voiceCommandsOn) {
      setVoiceCommandsOn(false);
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = lang === "mr" ? "mr-IN" : lang === "hi" ? "hi-IN" : "en-IN";
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript.toLowerCase();
      setStatusMsg(`Heard voice command: "${transcript}"`);
      if (
        transcript.includes("ambulance") ||
        transcript.includes("ॲम्ब्युलन्स") ||
        transcript.includes("एम्बुलेंस") ||
        transcript.includes("मदत")
      ) {
        startFiveSecondSosCountdown("VOICE_AMBULANCE");
      }
    };
    recognition.start();
    setVoiceCommandsOn(true);
  };

  const startFiveSecondSosCountdown = (triggerSource = "BUTTON") => {
    setSosDispatchedData(null);
    setSosCountdown(5);
    speakText("Calling ambulance in 5 seconds. Press cancel if accidental.", "en-IN");
    let remaining = 5;
    clearInterval(countdownTimerRef.current);
    countdownTimerRef.current = setInterval(async () => {
      remaining -= 1;
      if (remaining > 0) setSosCountdown(remaining);
      else {
        clearInterval(countdownTimerRef.current);
        setSosCountdown(null);
        const res = await api.post("/emergency/sos", {
          patient_id: patientId,
          triggered_via: triggerSource,
          latitude: 18.6298,
          longitude: 73.7997,
          countdown_completed: true,
        });
        setSosDispatchedData(res.data);
        if (res.data.local_voice_readout) {
          speakText(res.data.local_voice_readout.spoken_script, res.data.local_voice_readout.tts_locale);
        }
      }
    }, 1000);
  };

  const cancelSosCountdown = async () => {
    clearInterval(countdownTimerRef.current);
    setSosCountdown(null);
    await api.post("/emergency/sos", {
      patient_id: patientId,
      triggered_via: "BUTTON",
      latitude: 18.6298,
      longitude: 73.7997,
      countdown_completed: false,
    });
    setStatusMsg("Emergency SOS cancelled within 5-second window.");
  };

  const handleGeneratePin = async () => {
    const res = await api.post(
      `/patient/${patientId}/generate-pin`,
      {},
      { headers: { Authorization: `Bearer ${elderToken}` } }
    );
    setGeneratedPin(res.data);
    setPinInput(res.data.consultation_pin);
    setStatusMsg(`Generated 15-minute Consent PIN: ${res.data.consultation_pin}`);
  };

  const handlePlayMedReminder = async (med) => {
    const res = await api.get(`/patient/${patientId}/voice-reminder`, {
      params: { med_name: med.name, dosage: med.dosage, meal_timing: med.meal_timing, lang },
    });
    speakText(res.data.spoken_script, `${lang}-IN`);
    setStatusMsg(res.data.spoken_script);
  };

  const handleDoctorVerifyPin = async (doctorIdInput) => {
    try {
      const res = await api.post("/doctor/verify-pin", {
        patient_id: targetPatientId,
        doctor_id: doctorIdInput,
        pin: pinInput,
      });
      setDoctorToken(res.data.access_token);
      setStatusMsg(`Unlocked 30-min consultation access for patient ${targetPatientId}!`);
      await refreshDashboard(targetPatientId);
    } catch (err) {
      setStatusMsg(err.response?.data?.detail || "PIN verification failed");
    }
  };

  const handleDoctorUpdateFirstAid = async (faPayload) => {
    const res = await api.put(`/doctor/patient/${targetPatientId}/first-aid`, faPayload, {
      params: { caretaker_email: caretakerEmail },
      headers: { Authorization: `Bearer ${doctorToken}` },
    });
    localStorage.setItem("cached_first_aid_voice", JSON.stringify(res.data.first_aid.cached_local_voice));
    setStatusMsg("First-Aid updated, local voice cached, and caretaker notified!");
    await refreshDashboard(targetPatientId);
  };

  const handleDoctorDictate = async (dictationText) => {
    const res = await api.post(
      "/doctor/dictate-prescription",
      { transcript: dictationText },
      { headers: { Authorization: `Bearer ${doctorToken}` } }
    );
    setRxDraft(res.data);
    setStatusMsg("Gemini parsed dictation into structured medication course!");
  };

  const handleDoctorConfirmRx = async (nextApptDate) => {
    const res = await api.post(
      `/doctor/patient/${targetPatientId}/prescriptions`,
      { ...rxDraft, next_appointment_date: nextApptDate },
      {
        params: { caretaker_email: caretakerEmail },
        headers: { Authorization: `Bearer ${doctorToken}` },
      }
    );
    setCalendarSyncInfo(res.data.google_calendar_sync);
    setStatusMsg("Prescription saved, caretaker emailed, & synced to Google Calendar!");
    await refreshDashboard(targetPatientId);
  };

  if (!currentUser) {
    return (
      <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
        <LoginScreen onLogin={handleUserLogin} />
      </GoogleOAuthProvider>
    );
  }

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <div
        style={{
          minHeight: "100vh",
          backgroundColor: highContrast ? "#090D16" : "#F8FAFC",
          color: highContrast ? "#FFFFFF" : "#0F172A",
          fontFamily: "system-ui, sans-serif",
          padding: "1.5rem",
        }}
      >
        <Header
          title={t.title}
          currentUser={currentUser}
          lang={lang}
          onLanguageChange={handleLanguageChange}
          voiceCommandsOn={voiceCommandsOn}
          onToggleVoiceCommand={toggleVoiceCommandListener}
          highContrast={highContrast}
          onToggleContrast={() => setHighContrast(!highContrast)}
          onLogout={() => {
            setCurrentUser(null);
            setElderToken("");
            setDoctorToken("");
            setTargetPatientId("elder_101");
          }}
        />

        {statusMsg && (
          <div
            role="status"
            aria-live="polite"
            style={{
              backgroundColor: "#1E3A8A",
              color: "#FFF",
              padding: "1rem",
              borderRadius: "8px",
              marginBottom: "1.5rem",
              borderLeft: "6px solid #38BDF8",
            }}
          >
            {statusMsg}
          </div>
        )}

        {/* Emergency SOS Bar strictly shown ONLY to Elderly Patient */}
        {currentUser.role === "ELDER" && (
          <EmergencyBar
            t={t}
            sosCountdown={sosCountdown}
            sosDispatchedData={sosDispatchedData}
            onStartSos={startFiveSecondSosCountdown}
            onCancelSos={cancelSosCountdown}
          />
        )}

        {/* STRICT ROLE ISOLATION: Each role only sees their own portal */}
        {currentUser.role === "ELDER" && (
          <SeniorProtocol
            t={t}
            lang={lang}
            generatedPin={generatedPin}
            firstAid={firstAid}
            prescriptions={prescriptions}
            caretakers={caretakers}
            appointments={appointments}
            onGeneratePin={handleGeneratePin}
            onPlayMedReminder={handlePlayMedReminder}
            onRefresh={() => refreshDashboard(patientId)}
            elderToken={elderToken}
            patientId={patientId}
          />
        )}

        {currentUser.role === "DOCTOR" && (
          <DoctorProtocol
            targetPatientId={targetPatientId}
            setTargetPatientId={setTargetPatientId}
            pinInput={pinInput}
            setPinInput={setPinInput}
            doctorToken={doctorToken}
            patientProfile={patientProfile}
            patientWallet={patientWallet}
            caretakerEmail={caretakerEmail}
            setCaretakerEmail={setCaretakerEmail}
            onVerifyPin={handleDoctorVerifyPin}
            onUpdateFirstAid={handleDoctorUpdateFirstAid}
            onDictateRx={handleDoctorDictate}
            rxDraft={rxDraft}
            onConfirmRx={handleDoctorConfirmRx}
            calendarSyncInfo={calendarSyncInfo}
            onEndSession={() => setDoctorToken("")}
          />
        )}

        {currentUser.role === "CARETAKER" && (
          <CaretakerProtocol
            currentUser={currentUser}
            elderToken={elderToken}
            selectedPatientId={targetPatientId}
            onSelectPatient={async (pid) => {
              setTargetPatientId(pid);
              const tokRes = await api.get(`/demo/token/CARETAKER/${currentUser.email}`, {
                params: { linked_patient_id: pid },
              });
              setElderToken(tokRes.data.access_token);
              await refreshDashboard(pid);
            }}
            patientProfile={patientProfile}
            patientWallet={patientWallet}
            prescriptions={prescriptions}
            appointments={appointments}
            firstAid={firstAid}
            auditLogs={auditLogs}
            onRefresh={(pid) => refreshDashboard(pid)}
          />
        )}
      </div>
    </GoogleOAuthProvider>
  );
}