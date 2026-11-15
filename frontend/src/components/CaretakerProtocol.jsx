import React, { useState, useEffect } from "react";
import { Activity, Users, Calendar, User, CheckCircle2, FileText } from "lucide-react";
import { api } from "../services/api";

export default function CaretakerProtocol({
  currentUser,
  elderToken,
  selectedPatientId,
  onSelectPatient,
  patientProfile,
  patientWallet,
  prescriptions,
  appointments,
  firstAid,
  auditLogs,
  onRefresh,
}) {
  const [linkedPatients, setLinkedPatients] = useState([]);
  const [bloodType, setBloodType] = useState("");
  const [chronicDiseases, setChronicDiseases] = useState("");
  const [apptDoc, setApptDoc] = useState("");
  const [apptHosp, setApptHosp] = useState("");
  const [apptDate, setApptDate] = useState("2026-11-28");

  useEffect(() => {
    async function fetchLinked() {
      const res = await api.get("/caretaker/patients", {
        params: { email: currentUser.email },
      });
      const list = res.data.linked_patients || [];
      setLinkedPatients(list);
      if (list.length > 0 && !selectedPatientId) {
        onSelectPatient(list[0].patient_id);
      }
    }
    fetchLinked();
  }, [currentUser.email]);

  useEffect(() => {
    setBloodType(patientProfile?.blood_group || "");
    setChronicDiseases(patientProfile?.chronic_disorders || "");
  }, [patientProfile]);

  const handleCaretakerSaveProfile = async (e) => {
    e.preventDefault();
    await api.put(
      `/patient/${selectedPatientId}/profile`,
      { blood_group: bloodType, chronic_disorders: chronicDiseases },
      { headers: { Authorization: `Bearer ${elderToken}` } }
    );
    onRefresh(selectedPatientId);
  };

  const handleCaretakerAddAppt = async (e) => {
    e.preventDefault();
    await api.post(
      `/patient/${selectedPatientId}/appointments`,
      { doctor_name: apptDoc, hospital_name: apptHosp, appointment_date: apptDate },
      { headers: { Authorization: `Bearer ${elderToken}` } }
    );
    setApptDoc("");
    setApptHosp("");
    onRefresh(selectedPatientId);
  };

  // If no patient has added this caretaker's email yet
  if (linkedPatients.length === 0) {
    return (
      <main
        style={{
          backgroundColor: "#1E293B",
          padding: "2rem",
          borderRadius: "12px",
          border: "2px solid #FACC15",
          maxWidth: "650px",
          margin: "2rem auto",
          textAlign: "center",
        }}
      >
        <Users size={40} color="#FACC15" />
        <h2 style={{ color: "#FACC15" }}>No Linked Elderly Patients Found Yet</h2>
        <p style={{ color: "#CBD5E1", fontSize: "1.05rem" }}>
          Your email (<strong>{currentUser.email}</strong>) has not been added by a patient yet.
        </p>
        <p style={{ color: "#94A3B8" }}>
          <strong>How to link:</strong> Log in to the <strong>Elderly Patient Portal</strong>, go to the{" "}
          <em>"Family & Caretaker Access"</em> card, and add <strong>{currentUser.email}</strong>. Once added, that patient's account will appear here for you to monitor and manage!
        </p>
      </main>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Top Bar: Select Which Linked Patient Account to Monitor */}
      <section
        style={{
          backgroundColor: "#1E293B",
          padding: "1.25rem",
          borderRadius: "12px",
          border: "2px solid #4ADE80",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div>
          <h2 style={{ margin: 0, color: "#4ADE80", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Users size={24} /> Select Linked Elderly Patient to Monitor
          </h2>
          <p style={{ margin: "0.25rem 0 0", color: "#CBD5E1", fontSize: "0.95rem" }}>
            Showing patients who have granted caretaker access to <strong>{currentUser.email}</strong>
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
          {linkedPatients.map((lp) => (
            <button
              key={lp.patient_id}
              onClick={() => onSelectPatient(lp.patient_id)}
              style={{
                padding: "0.6rem 1.2rem",
                borderRadius: "8px",
                fontWeight: "bold",
                border: selectedPatientId === lp.patient_id ? "2px solid #FACC15" : "1px solid #475569",
                backgroundColor: selectedPatientId === lp.patient_id ? "#0F172A" : "transparent",
                color: selectedPatientId === lp.patient_id ? "#FACC15" : "#FFF",
                cursor: "pointer",
              }}
            >
              👵 Patient ID: {lp.patient_id} ({lp.relation})
            </button>
          ))}
        </div>
      </section>

      {/* Caretaker Management Row: Edit Patient Profile & Schedule Appointments */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
          <h3 style={{ marginTop: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <User size={20} color="#38BDF8" /> Manage {selectedPatientId}'s Medical Profile
          </h3>
          <form onSubmit={handleCaretakerSaveProfile} style={{ display: "grid", gap: "0.65rem" }}>
            <input
              value={bloodType}
              onChange={(e) => setBloodType(e.target.value)}
              placeholder="Blood Group (e.g. O+)"
              style={{ padding: "0.6rem", borderRadius: "6px" }}
            />
            <input
              value={chronicDiseases}
              onChange={(e) => setChronicDiseases(e.target.value)}
              placeholder="Chronic Conditions / Allergies"
              style={{ padding: "0.6rem", borderRadius: "6px" }}
            />
            <button
              type="submit"
              style={{ padding: "0.65rem", backgroundColor: "#38BDF8", color: "#000", fontWeight: "bold", border: "none", borderRadius: "6px", cursor: "pointer" }}
            >
              Update Patient Profile on Behalf of Elder
            </button>
          </form>
        </div>

        <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
          <h3 style={{ marginTop: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Calendar size={20} color="#FACC15" /> Book Appointment for {selectedPatientId}
          </h3>
          <form onSubmit={handleCaretakerAddAppt} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem" }}>
            <input value={apptDoc} onChange={(e) => setApptDoc(e.target.value)} placeholder="Doctor Name" required style={{ padding: "0.6rem", borderRadius: "6px" }} />
            <input value={apptHosp} onChange={(e) => setApptHosp(e.target.value)} placeholder="Hospital Name" required style={{ padding: "0.6rem", borderRadius: "6px" }} />
            <input type="date" value={apptDate} onChange={(e) => setApptDate(e.target.value)} required style={{ padding: "0.6rem", borderRadius: "6px" }} />
            <button type="submit" style={{ padding: "0.6rem", backgroundColor: "#FACC15", color: "#000", fontWeight: "bold", border: "none", borderRadius: "6px", cursor: "pointer" }}>
              + Schedule & Sync
            </button>
          </form>
          {appointments.length > 0 && (
            <ul style={{ listStyle: "none", padding: 0, marginTop: "0.75rem", marginBottom: 0 }}>
              {appointments.map((a, i) => (
                <li key={i} style={{ fontSize: "0.9rem", padding: "0.4rem 0", color: "#CBD5E1" }}>
                  • <strong>{a.doctor_name}</strong> ({a.hospital_name}) on {a.appointment_date}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Health Wallet Documents */}
      <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
        <h3 style={{ marginTop: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <FileText size={20} color="#FACC15" /> {selectedPatientId}'s Health Wallet (Reports & Scans)
        </h3>
        {patientWallet && patientWallet.length > 0 ? (
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {patientWallet.map((doc, i) => (
              <li key={i} style={{ padding: "0.65rem", backgroundColor: "#0F172A", borderRadius: "6px", marginBottom: "0.4rem", fontSize: "0.9rem", borderLeft: "3px solid #FACC15", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span>
                  <strong>{doc.title}</strong>{" "}
                  <span style={{ color: "#22C55E", fontSize: "0.8rem" }}>✓ {doc.status || "Stored"}</span>
                </span>
                {doc.preview_url && (
                  <a href={doc.preview_url} target="_blank" rel="noreferrer" style={{ color: "#38BDF8", fontSize: "0.85rem", fontWeight: "bold", whiteSpace: "nowrap", marginLeft: "0.75rem" }}>
                    [View Document ↗]
                  </a>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p style={{ color: "#94A3B8" }}>No uploaded reports in the wallet yet.</p>
        )}
      </div>

      {/* Patient Courses & Immutable Audit Trail */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
          <h3 style={{ marginTop: 0 }}>
            <CheckCircle2 size={20} color="#4ADE80" style={{ verticalAlign: "middle" }} /> Active Medication Courses & First Aid
          </h3>
          {firstAid && (
            <div style={{ padding: "0.75rem", backgroundColor: "#0F172A", borderRadius: "6px", marginBottom: "1rem", borderLeft: "4px solid #22C55E" }}>
              <strong>First Aid ({firstAid.condition_trigger}):</strong> {firstAid.immediate_steps.join(" ")}
            </div>
          )}
          {prescriptions.length === 0 ? (
            <p style={{ color: "#94A3B8" }}>No prescriptions recorded yet.</p>
          ) : (
            prescriptions.map((rx, i) => (
              <div key={i} style={{ padding: "0.75rem", backgroundColor: "#0F172A", borderRadius: "6px", marginBottom: "0.5rem", borderLeft: "4px solid #38BDF8" }}>
                <strong>{rx.diagnosis_notes}</strong> ({rx.is_completed ? "Completed" : "Ongoing"})
                <div style={{ fontSize: "0.9rem", color: "#CBD5E1" }}>
                  {rx.medications.map((m) => `${m.name} (${m.dosage})`).join(", ")}
                </div>
              </div>
            ))
          )}
        </div>

        <div style={{ backgroundColor: "#1E293B", padding: "1.5rem", borderRadius: "12px", border: "2px solid #475569" }}>
          <h3 style={{ marginTop: 0 }}>
            <Activity size={20} color="#FACC15" style={{ verticalAlign: "middle" }} /> Immutable Security Audit Trail ({selectedPatientId})
          </h3>
          {auditLogs.length === 0 ? (
            <p style={{ color: "#94A3B8" }}>No audit events recorded yet.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, maxHeight: "280px", overflowY: "auto" }}>
              {auditLogs.map((log, i) => (
                <li key={i} style={{ padding: "0.75rem", backgroundColor: "#0F172A", marginBottom: "0.5rem", borderRadius: "6px", borderLeft: "4px solid #FACC15", fontSize: "0.9rem" }}>
                  <strong>[{log.actor_role}] {log.actor_id}:</strong> {log.action_summary}
                  <div style={{ fontSize: "0.75rem", color: "#94A3B8", marginTop: "0.2rem" }}>{log.timestamp}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}