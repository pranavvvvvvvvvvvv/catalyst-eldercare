import React, { useState, useEffect } from "react";
import {
  QrCode,
  HeartPulse,
  Volume2,
  User,
  FileText,
  Upload,
  Calendar,
  Users,
  CheckCircle2,
  History,
} from "lucide-react";
import { api, speakText } from "../services/api";

export default function SeniorProtocol({
  t,
  lang,
  generatedPin,
  firstAid,
  prescriptions,
  caretakers,
  appointments,
  onGeneratePin,
  onPlayMedReminder,
  onRefresh,
  elderToken,
  patientId,
}) {
  const [bloodType, setBloodType] = useState("");
  const [chronicDiseases, setChronicDiseases] = useState("");
  const [walletFiles, setWalletFiles] = useState([]);
  const [saveStatus, setSaveStatus] = useState("");
  const [medView, setMedView] = useState("ONGOING"); // ONGOING | PAST

  // Caretaker Form State
  const [ctName, setCtName] = useState("");
  const [ctRelation, setCtRelation] = useState("Son / Daughter");
  const [ctEmail, setCtEmail] = useState("");

  // Appointment Form State
  const [apptDoc, setApptDoc] = useState("");
  const [apptHosp, setApptHosp] = useState("");
  const [apptDate, setApptDate] = useState("2026-11-25");

  useEffect(() => {
    if (!elderToken) return;
    api
      .get(`/patient/${patientId}/profile`, {
        headers: { Authorization: `Bearer ${elderToken}` },
      })
      .then((res) => {
        setBloodType(res.data.profile.blood_group || "");
        setChronicDiseases(res.data.profile.chronic_disorders || "");
        setWalletFiles(res.data.wallet || []);
      })
      .catch((err) => console.error("Failed to load profile", err));
  }, [elderToken, patientId]);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    await api.put(
      `/patient/${patientId}/profile`,
      { blood_group: bloodType, chronic_disorders: chronicDiseases },
      { headers: { Authorization: `Bearer ${elderToken}` } }
    );
    setSaveStatus("Saved!");
    setTimeout(() => setSaveStatus(""), 2500);
    onRefresh();
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    const res = await api.post(`/patient/${patientId}/wallet/upload`, formData, {
      headers: {
        Authorization: `Bearer ${elderToken}`,
        "Content-Type": "multipart/form-data",
      },
    });
    setWalletFiles([...walletFiles, res.data.file]);
    onRefresh();
  };

  const handleAddCaretaker = async (e) => {
    e.preventDefault();
    await api.post(
      `/patient/${patientId}/caretakers`,
      { name: ctName, relation: ctRelation, email: ctEmail },
      { headers: { Authorization: `Bearer ${elderToken}` } }
    );
    setCtName("");
    setCtEmail("");
    onRefresh();
  };

  const handleAddAppointment = async (e) => {
    e.preventDefault();
    await api.post(
      `/patient/${patientId}/appointments`,
      { doctor_name: apptDoc, hospital_name: apptHosp, appointment_date: apptDate },
      { headers: { Authorization: `Bearer ${elderToken}` } }
    );
    setApptDoc("");
    setApptHosp("");
    onRefresh();
  };

  const handleMarkCourseCompleted = async (idx) => {
    await api.put(
      `/patient/${patientId}/prescriptions/${idx}/complete`,
      {},
      { headers: { Authorization: `Bearer ${elderToken}` } }
    );
    onRefresh();
  };

  const ongoingList = prescriptions.map((r, i) => ({ ...r, idx: i })).filter((r) => !r.is_completed);
  const pastList = prescriptions.map((r, i) => ({ ...r, idx: i })).filter((r) => r.is_completed);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* ROW 1: Clinic PIN Pass & Ongoing/Past Medication Routine */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.25fr", gap: "1.5rem" }}>
        {/* Clinic Pass + First Aid */}
        <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: 0 }}>
              <QrCode size={26} color="#38BDF8" /> Doctor Consent Pass
            </h2>
            <span style={{ backgroundColor: "#0F172A", padding: "0.3rem 0.7rem", borderRadius: "6px", color: "#FACC15", fontSize: "0.9rem" }}>
              Your Patient ID: <strong>{patientId}</strong>
            </span>
          </div>
          <p style={{ color: "#CBD5E1" }}>
            Share your Patient ID (<strong>{patientId}</strong>) and this 15-minute one-time PIN with your doctor during a clinic visit.
          </p>
          <button
            onClick={onGeneratePin}
            style={{ width: "100%", minHeight: "54px", fontSize: "1.15rem", fontWeight: "bold", backgroundColor: "#38BDF8", color: "#000", border: "none", borderRadius: "8px", cursor: "pointer" }}
          >
            {t.generatingPin}
          </button>

          {generatedPin && (
            <div style={{ marginTop: "1rem", padding: "1rem", backgroundColor: "#0F172A", borderRadius: "8px", textAlign: "center", border: "2px dashed #FACC15" }}>
              <div style={{ fontSize: "0.9rem", color: "#94A3B8" }}>15-MINUTE ONE-TIME CONSENT PIN</div>
              <div style={{ fontSize: "2.6rem", fontWeight: "bold", letterSpacing: "6px", color: "#FACC15" }}>
                {generatedPin.consultation_pin}
              </div>
            </div>
          )}

          <div style={{ marginTop: "1.5rem", padding: "1rem", backgroundColor: "#0F172A", borderRadius: "8px", borderLeft: "5px solid #22C55E" }}>
            <h3 style={{ margin: "0 0 0.5rem", color: "#4ADE80" }}>
              <HeartPulse size={20} style={{ verticalAlign: "middle" }} /> {t.firstAidTitle}
            </h3>
            {firstAid ? (
              <>
                <p style={{ margin: "0.25rem 0", fontWeight: "bold" }}>
                  {firstAid.condition_trigger} (Dr. {firstAid.updated_by_doctor_id})
                </p>
                <p style={{ margin: "0.25rem 0" }}>{firstAid.immediate_steps.join(" ")}</p>
                <button
                  onClick={() => {
                    const voiceObj = firstAid.cached_local_voice?.[lang];
                    if (voiceObj) speakText(voiceObj.spoken_script, voiceObj.tts_locale);
                  }}
                  style={{ marginTop: "0.5rem", padding: "0.5rem 1rem", backgroundColor: "#22C55E", color: "#000", fontWeight: "bold", border: "none", borderRadius: "6px", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.4rem" }}
                >
                  <Volume2 size={20} /> {t.readAloud} ({lang.toUpperCase()})
                </button>
              </>
            ) : (
              <p style={{ color: "#94A3B8" }}>No custom first-aid protocol assigned by your doctor yet.</p>
            )}
          </div>
        </div>

        {/* Ongoing Routine & Past Medications */}
        <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h2 style={{ margin: 0 }}>{t.ongoingMeds}</h2>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                onClick={() => setMedView("ONGOING")}
                style={{ padding: "0.45rem 0.9rem", borderRadius: "6px", fontWeight: "bold", border: "none", cursor: "pointer", backgroundColor: medView === "ONGOING" ? "#38BDF8" : "#0F172A", color: medView === "ONGOING" ? "#000" : "#FFF" }}
              >
                Ongoing ({ongoingList.length})
              </button>
              <button
                onClick={() => setMedView("PAST")}
                style={{ padding: "0.45rem 0.9rem", borderRadius: "6px", fontWeight: "bold", border: "none", cursor: "pointer", backgroundColor: medView === "PAST" ? "#FACC15" : "#0F172A", color: medView === "PAST" ? "#000" : "#FFF", display: "flex", alignItems: "center", gap: "0.3rem" }}
              >
                <History size={16} /> Past History ({pastList.length})
              </button>
            </div>
          </div>

          {(medView === "ONGOING" ? ongoingList : pastList).length === 0 ? (
            <p style={{ color: "#94A3B8" }}>
              {medView === "ONGOING"
                ? "No active medication courses right now."
                : "No completed past medication courses yet."}
            </p>
          ) : (
            (medView === "ONGOING" ? ongoingList : pastList).map((rx) => (
              <div key={rx.idx} style={{ backgroundColor: "#0F172A", padding: "1rem", borderRadius: "8px", marginBottom: "1rem", borderLeft: `5px solid ${medView === "ONGOING" ? "#38BDF8" : "#94A3B8"}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontWeight: "bold", color: "#38BDF8" }}>
                    Diagnosis: {rx.diagnosis_notes} (Dr. {rx.doctor_id})
                  </div>
                  {medView === "ONGOING" && (
                    <button
                      onClick={() => handleMarkCourseCompleted(rx.idx)}
                      style={{ padding: "0.3rem 0.65rem", fontSize: "0.8rem", backgroundColor: "#22C55E", color: "#000", border: "none", borderRadius: "4px", fontWeight: "bold", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.25rem" }}
                    >
                      <CheckCircle2 size={14} /> Complete Course
                    </button>
                  )}
                </div>
                {rx.medications.map((m, mIdx) => (
                  <div key={mIdx} style={{ marginTop: "0.75rem", padding: "0.75rem", backgroundColor: "#1E293B", borderRadius: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <strong style={{ fontSize: "1.15rem", color: "#FACC15" }}>{m.name} ({m.dosage})</strong>
                      <div style={{ fontSize: "0.95rem", marginTop: "0.2rem" }}>
                        {[m.morning && "🌅 Morning", m.afternoon && "☀️ Afternoon", m.evening && "🌙 Evening"].filter(Boolean).join(" • ")} | <strong>{m.meal_timing === "BEFORE_MEAL" ? t.beforeMeal : t.afterMeal}</strong>
                      </div>
                    </div>
                    <button
                      onClick={() => onPlayMedReminder(m)}
                      style={{ padding: "0.5rem 1rem", backgroundColor: "#38BDF8", color: "#000", fontWeight: "bold", border: "none", borderRadius: "6px", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.4rem" }}
                    >
                      <Volume2 size={18} /> {t.readAloud}
                    </button>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      </div>

      {/* ROW 2: Add Family Caretaker Access & Manage Appointments */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        {/* Grant Family / Caretaker Portal Access */}
        <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
          <h2 style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: 0 }}>
            <Users size={24} color="#4ADE80" /> Family & Caretaker Access
          </h2>
          <p style={{ color: "#94A3B8", fontSize: "0.95rem", marginTop: 0 }}>
            Add a trusted family member or caretaker to give them Caretaker Portal access and instant email alerts.
          </p>
          <form onSubmit={handleAddCaretaker} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem" }}>
            <input
              value={ctName}
              onChange={(e) => setCtName(e.target.value)}
              placeholder="Member Name (e.g. Rahul)"
              required
              style={{ padding: "0.6rem", borderRadius: "6px" }}
            />
            <input
              value={ctRelation}
              onChange={(e) => setCtRelation(e.target.value)}
              placeholder="Relation (e.g. Son)"
              required
              style={{ padding: "0.6rem", borderRadius: "6px" }}
            />
            <input
              type="email"
              value={ctEmail}
              onChange={(e) => setCtEmail(e.target.value)}
              placeholder="Caretaker Email for Alerts"
              required
              style={{ gridColumn: "span 2", padding: "0.6rem", borderRadius: "6px" }}
            />
            <button
              type="submit"
              style={{ gridColumn: "span 2", padding: "0.7rem", backgroundColor: "#4ADE80", color: "#000", fontWeight: "bold", border: "none", borderRadius: "6px", cursor: "pointer" }}
            >
              + Grant Caretaker Portal Access
            </button>
          </form>

          {caretakers.length > 0 && (
            <ul style={{ listStyle: "none", padding: 0, marginTop: "1rem", marginBottom: 0 }}>
              {caretakers.map((c, i) => (
                <li key={i} style={{ padding: "0.65rem", backgroundColor: "#0F172A", borderRadius: "6px", marginBottom: "0.4rem", borderLeft: "4px solid #4ADE80", fontSize: "0.92rem" }}>
                  <strong>{c.name}</strong> ({c.relation}) — <span style={{ color: "#38BDF8" }}>{c.email}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Add & View Upcoming Appointments */}
        <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
          <h2 style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: 0 }}>
            <Calendar size={24} color="#FACC15" /> Upcoming Appointments
          </h2>
          <form onSubmit={handleAddAppointment} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem" }}>
            <input
              value={apptDoc}
              onChange={(e) => setApptDoc(e.target.value)}
              placeholder="Doctor Name (e.g. Dr. Patil)"
              required
              style={{ padding: "0.6rem", borderRadius: "6px" }}
            />
            <input
              value={apptHosp}
              onChange={(e) => setApptHosp(e.target.value)}
              placeholder="Clinic / Hospital Name"
              required
              style={{ padding: "0.6rem", borderRadius: "6px" }}
            />
            <input
              type="date"
              value={apptDate}
              onChange={(e) => setApptDate(e.target.value)}
              required
              style={{ padding: "0.6rem", borderRadius: "6px" }}
            />
            <button
              type="submit"
              style={{ padding: "0.6rem", backgroundColor: "#FACC15", color: "#000", fontWeight: "bold", border: "none", borderRadius: "6px", cursor: "pointer" }}
            >
              + Add & Sync Calendar
            </button>
          </form>

          {appointments.length > 0 && (
            <ul style={{ listStyle: "none", padding: 0, marginTop: "1rem", marginBottom: 0 }}>
              {appointments.map((a, i) => (
                <li key={i} style={{ padding: "0.65rem", backgroundColor: "#0F172A", borderRadius: "6px", marginBottom: "0.4rem", borderLeft: "4px solid #FACC15", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <strong>{a.doctor_name}</strong> at {a.hospital_name} ({a.appointment_date})
                  </div>
                  <a href={a.google_calendar_deep_link} target="_blank" rel="noreferrer" style={{ color: "#38BDF8", fontSize: "0.85rem", fontWeight: "bold" }}>
                    Google Calendar ↗
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* ROW 3: Medical Profile & Health Wallet */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
          <h2 style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: 0 }}>
            <User size={24} color="#38BDF8" /> Personal Medical Profile
          </h2>
          <form onSubmit={handleSaveProfile} style={{ display: "grid", gap: "0.75rem" }}>
            <label style={{ color: "#CBD5E1" }}>
              Blood Type:
              <select value={bloodType} onChange={(e) => setBloodType(e.target.value)} style={{ width: "100%", padding: "0.6rem", marginTop: "0.25rem", borderRadius: "6px" }}>
                <option value="">Select Blood Type</option>
                {["A+", "O+", "B+", "AB+", "A-", "O-", "B-", "AB-"].map((bg) => (
                  <option key={bg} value={bg}>{bg}</option>
                ))}
              </select>
            </label>
            <label style={{ color: "#CBD5E1" }}>
              Chronic Diseases / Allergies:
              <input
                type="text"
                value={chronicDiseases}
                onChange={(e) => setChronicDiseases(e.target.value)}
                placeholder="e.g. Type 2 Diabetes, Hypertension"
                style={{ width: "100%", padding: "0.6rem", marginTop: "0.25rem", borderRadius: "6px" }}
              />
            </label>
            <button type="submit" style={{ padding: "0.75rem", backgroundColor: "#22C55E", color: "#000", fontWeight: "bold", border: "none", borderRadius: "6px", cursor: "pointer" }}>
              {saveStatus || "Save Profile Info"}
            </button>
          </form>
        </div>

        <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
          <h2 style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: 0 }}>
            <FileText size={24} color="#FACC15" /> Secure Health Wallet (Reports & Scans)
          </h2>
          <label style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "0.5rem", padding: "1rem", border: "2px dashed #38BDF8", borderRadius: "8px", cursor: "pointer", backgroundColor: "#0F172A", color: "#38BDF8", fontWeight: "bold" }}>
            <Upload size={20} /> Upload Medical Report (PDF / JPEG)
            <input type="file" accept=".pdf, .jpg, .jpeg, .png" onChange={handleFileUpload} style={{ display: "none" }} />
          </label>
          {walletFiles.length > 0 && (
            <ul style={{ listStyle: "none", padding: 0, marginTop: "1rem", marginBottom: 0 }}>
              {walletFiles.map((f, i) => (
                <li key={i} style={{ padding: "0.65rem", backgroundColor: "#0F172A", borderRadius: "6px", marginBottom: "0.4rem", fontSize: "0.9rem", borderLeft: "3px solid #FACC15", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span>
                    <strong>{f.title}</strong> <span style={{ color: "#22C55E", fontSize: "0.8rem" }}>✓ {f.status}</span>
                  </span>
                  {f.preview_url && (
                    <a href={f.preview_url} target="_blank" rel="noreferrer" style={{ color: "#38BDF8", fontSize: "0.85rem", fontWeight: "bold", whiteSpace: "nowrap", marginLeft: "0.75rem" }}>
                      [View Document ↗]
                    </a>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}