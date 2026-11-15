import React, { useState } from "react";
import { UserCheck, Mic, Calendar, FileText, HeartHandshake, Lock } from "lucide-react";

export default function DoctorProtocol({
  targetPatientId,
  setTargetPatientId,
  pinInput,
  setPinInput,
  doctorToken,
  patientProfile,
  patientWallet,
  caretakerEmail,
  setCaretakerEmail,
  onVerifyPin,
  onUpdateFirstAid,
  onDictateRx,
  rxDraft,
  onConfirmRx,
  calendarSyncInfo,
  onEndSession,
}) {
  const [doctorIdInput, setDoctorIdInput] = useState("dr_kulkarni");
  const [faTrigger, setFaTrigger] = useState("Sudden chest heaviness or dizziness");
  const [faSteps, setFaSteps] = useState("Keep patient seated upright. Place 1 Sorbitrate 5mg under tongue.");
  const [faDoNot, setFaDoNot] = useState("Do not allow the patient to walk or climb stairs.");
  const [dictationText, setDictationText] = useState(
    "Mild hypertension. Take Amlodipine 5mg morning and evening after meal for 30 days."
  );
  const [nextApptDate, setNextApptDate] = useState("2026-11-25");

  // GATEKEEPER: If no patient PIN is verified yet, ONLY show the PIN Unlock screen!
  if (!doctorToken) {
    return (
      <main style={{ maxWidth: "520px", margin: "3rem auto" }}>
        <div
          style={{
            backgroundColor: "#1E293B",
            padding: "2rem",
            borderRadius: "14px",
            border: "2px solid #FACC15",
          }}
        >
          <h2 style={{ marginTop: 0, color: "#FACC15", display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <Lock size={26} /> Unlock Patient Consultation Session
          </h2>
          <p style={{ color: "#CBD5E1", fontSize: "0.95rem", marginBottom: "1.25rem" }}>
            Prescription tools, First-Aid protocols, and the Patient Health Wallet are hidden until the patient grants consent via their 15-minute 6-digit PIN.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              onVerifyPin(doctorIdInput);
            }}
            style={{ display: "grid", gap: "0.9rem" }}
          >
            <label style={{ fontSize: "0.9rem", color: "#94A3B8" }}>
              Your Doctor ID:
              <input
                value={doctorIdInput}
                onChange={(e) => setDoctorIdInput(e.target.value)}
                placeholder="Doctor ID (e.g. dr_kulkarni)"
                required
                style={{ width: "100%", padding: "0.65rem", marginTop: "0.3rem", borderRadius: "6px" }}
              />
            </label>
            <label style={{ fontSize: "0.9rem", color: "#94A3B8" }}>
              Patient Unique ID:
              <input
                value={targetPatientId}
                onChange={(e) => setTargetPatientId(e.target.value)}
                placeholder="Target Patient ID (e.g. elder_101)"
                required
                style={{ width: "100%", padding: "0.65rem", marginTop: "0.3rem", borderRadius: "6px" }}
              />
            </label>
            <label style={{ fontSize: "0.9rem", color: "#94A3B8" }}>
              6-Digit Patient Consent PIN:
              <input
                value={pinInput}
                onChange={(e) => setPinInput(e.target.value)}
                placeholder="Enter 6-Digit PIN from Patient"
                required
                style={{ width: "100%", padding: "0.75rem", marginTop: "0.3rem", fontSize: "1.25rem", letterSpacing: "4px", borderRadius: "6px" }}
              />
            </label>
            <button
              type="submit"
              style={{
                minHeight: "52px",
                backgroundColor: "#FACC15",
                color: "#000",
                fontWeight: "bold",
                fontSize: "1.05rem",
                border: "none",
                borderRadius: "8px",
                cursor: "pointer",
                marginTop: "0.5rem",
              }}
            >
              Verify PIN & Open Patient Consultation
            </button>
          </form>
        </div>
      </main>
    );
  }

  // UNLOCKED VIEW: Visible ONLY after valid PIN verification
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <section
        style={{
          backgroundColor: "#064E3B",
          border: "2px solid #22C55E",
          borderRadius: "12px",
          padding: "1.25rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div>
          <h3 style={{ margin: "0 0 0.5rem", color: "#4ADE80", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <HeartHandshake size={22} /> Active Consultation: Patient {targetPatientId} (30-Min Scoped Access)
          </h3>
          <p style={{ margin: "0.25rem 0" }}>
            <strong>Blood Group:</strong> {patientProfile?.blood_group || "Not specified"} |{" "}
            <strong>Chronic Conditions:</strong> {patientProfile?.chronic_disorders || "None reported"}
          </p>
          <div style={{ marginTop: "0.5rem" }}>
            <strong><FileText size={16} style={{ verticalAlign: "middle" }} /> Health Wallet Reports: </strong>
            {patientWallet && patientWallet.length > 0 ? (
              patientWallet.map((f, i) => (
                <span key={i} style={{ marginRight: "1rem" }}>
                  {f.title}{" "}
                  {f.preview_url && (
                    <a href={f.preview_url} target="_blank" rel="noreferrer" style={{ color: "#38BDF8" }}>
                      [Open Report ↗]
                    </a>
                  )}
                </span>
              ))
            ) : (
              "No uploaded reports in wallet yet."
            )}
          </div>
        </div>
        <button
          onClick={onEndSession}
          style={{
            padding: "0.6rem 1.2rem",
            backgroundColor: "#EF4444",
            color: "#FFF",
            fontWeight: "bold",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
          }}
        >
          End Consultation Session
        </button>
      </section>

      <main style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        {/* Left Column: Update Emergency First Aid */}
        <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
          <h2 style={{ marginTop: 0 }}>
            <UserCheck size={24} style={{ verticalAlign: "middle" }} /> 1. Update Emergency First Aid Protocol
          </h2>
          <p style={{ color: "#94A3B8", fontSize: "0.9rem" }}>
            Saves directly to {targetPatientId}'s profile and pre-caches English, Hindi, and Marathi voice instructions.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              onUpdateFirstAid({
                condition_trigger: faTrigger,
                immediate_steps: [faSteps],
                do_not_do: faDoNot,
                updated_by_doctor_id: doctorIdInput,
              });
            }}
            style={{ display: "grid", gap: "0.75rem" }}
          >
            <input value={faTrigger} onChange={(e) => setFaTrigger(e.target.value)} placeholder="Condition trigger" style={{ padding: "0.6rem", borderRadius: "6px" }} />
            <textarea rows={3} value={faSteps} onChange={(e) => setFaSteps(e.target.value)} placeholder="Immediate First-Aid steps" style={{ padding: "0.6rem", borderRadius: "6px" }} />
            <input value={faDoNot} onChange={(e) => setFaDoNot(e.target.value)} placeholder="Do Not Do warning" style={{ padding: "0.6rem", borderRadius: "6px" }} />
            <button
              type="submit"
              style={{ minHeight: "48px", backgroundColor: "#22C55E", color: "#000", fontWeight: "bold", border: "none", borderRadius: "6px", cursor: "pointer" }}
            >
              Save First Aid & Cache Local Voice (EN/HI/MR)
            </button>
          </form>
        </div>

        {/* Right Column: Gemini Dictation & Google Calendar Sync */}
        <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
          <h2 style={{ marginTop: 0 }}>
            <Mic size={24} style={{ verticalAlign: "middle" }} /> 2. Gemini Voice-to-Prescription
          </h2>
          <label style={{ display: "block", marginBottom: "0.6rem", fontSize: "0.9rem" }}>
            Caretaker Notification Email:
            <input
              type="email"
              value={caretakerEmail}
              onChange={(e) => setCaretakerEmail(e.target.value)}
              style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem", borderRadius: "6px" }}
            />
          </label>
          <textarea rows={3} value={dictationText} onChange={(e) => setDictationText(e.target.value)} style={{ width: "100%", padding: "0.6rem", borderRadius: "6px" }} />
          <button
            onClick={() => onDictateRx(dictationText)}
            style={{ width: "100%", marginTop: "0.75rem", minHeight: "48px", backgroundColor: "#38BDF8", color: "#000", fontWeight: "bold", border: "none", borderRadius: "6px", cursor: "pointer" }}
          >
            Parse Dictation with Gemini AI
          </button>

          {rxDraft && (
            <div style={{ marginTop: "1rem", padding: "1rem", backgroundColor: "#0F172A", borderRadius: "8px" }}>
              <h4 style={{ margin: "0 0 0.5rem", color: "#FACC15" }}>Structured Course Preview:</h4>
              <pre style={{ fontSize: "0.82rem", overflowX: "auto", color: "#38BDF8" }}>{JSON.stringify(rxDraft, null, 2)}</pre>
              <label style={{ display: "block", marginTop: "0.75rem" }}>
                Next Appointment Date:
                <input type="date" value={nextApptDate} onChange={(e) => setNextApptDate(e.target.value)} style={{ marginLeft: "0.5rem", padding: "0.4rem", borderRadius: "4px" }} />
              </label>
              <button
                onClick={() => onConfirmRx(nextApptDate)}
                style={{ width: "100%", marginTop: "0.75rem", minHeight: "48px", backgroundColor: "#22C55E", color: "#000", fontWeight: "bold", border: "none", borderRadius: "6px", cursor: "pointer" }}
              >
                Confirm Course, Email Caretaker & Sync Calendar
              </button>
            </div>
          )}

          {calendarSyncInfo && (
            <div style={{ marginTop: "1rem", padding: "0.75rem", backgroundColor: "#064E3B", borderRadius: "8px" }}>
              <Calendar size={18} style={{ verticalAlign: "middle" }} /> <strong>Google Calendar Synced!</strong>{" "}
              <a href={calendarSyncInfo.google_calendar_deep_link} target="_blank" rel="noreferrer" style={{ color: "#A7F3D0", marginLeft: "0.5rem" }}>
                Open Event in Google Calendar
              </a>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}