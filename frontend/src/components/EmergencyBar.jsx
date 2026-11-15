import React from "react";
import { ShieldAlert } from "lucide-react";

export default function EmergencyBar({
  t,
  sosCountdown,
  sosDispatchedData,
  onStartSos,
  onCancelSos,
}) {
  return (
    <section
      aria-label="Emergency SOS Controls"
      style={{
        backgroundColor: "#450A0A",
        border: "3px solid #EF4444",
        borderRadius: "12px",
        padding: "1.25rem",
        marginBottom: "1.75rem",
      }}
    >
      {sosCountdown !== null ? (
        <div role="alert" aria-live="assertive" style={{ textAlign: "center" }}>
          <h2 style={{ fontSize: "1.8rem", color: "#FCA5A5", margin: "0 0 1rem" }}>
            🚨 Calling Ambulance & Alerting Caretakers in {sosCountdown} seconds...
          </h2>
          <button
            onClick={onCancelSos}
            style={{
              minHeight: "60px",
              padding: "0.9rem 2.2rem",
              fontSize: "1.4rem",
              fontWeight: "bold",
              backgroundColor: "#FACC15",
              color: "#000",
              border: "none",
              borderRadius: "10px",
              cursor: "pointer",
            }}
          >
            ✋ {t.cancelSos}
          </button>
        </div>
      ) : (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: "1.35rem", color: "#FECACA" }}>
              24/7 Smart Emergency Protection
            </h2>
            <p style={{ margin: "0.25rem 0 0", color: "#FCA5A5" }}>
              5-second accidental-tap cancellation window + live GPS & Doctor First Aid
            </p>
          </div>
          <button
            onClick={() => onStartSos("BUTTON")}
            style={{
              minHeight: "58px",
              padding: "0.75rem 1.75rem",
              fontSize: "1.2rem",
              fontWeight: "bold",
              backgroundColor: "#EF4444",
              color: "#FFF",
              border: "3px solid #FFF",
              borderRadius: "10px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.6rem",
            }}
          >
            <ShieldAlert size={26} /> {t.sosBtn}
          </button>
        </div>
      )}

      {sosDispatchedData && (
        <div
          role="alert"
          style={{
            marginTop: "1.25rem",
            padding: "1.25rem",
            backgroundColor: "#000",
            borderRadius: "8px",
            border: "2px solid #FACC15",
          }}
        >
          <h3 style={{ color: "#FACC15", fontSize: "1.4rem", margin: "0 0 0.5rem" }}>
            🚑 SOS DISPATCHED! Live Location:{" "}
            <a
              href={sosDispatchedData.live_location_google_maps}
              target="_blank"
              rel="noreferrer"
              style={{ color: "#38BDF8" }}
            >
              Open Google Maps Coordinates
            </a>
          </h3>
          {sosDispatchedData.doctor_recommended_first_aid ? (
            <div>
              <p style={{ fontSize: "1.15rem", fontWeight: "bold", margin: "0.5rem 0" }}>
                Doctor First Aid ({sosDispatchedData.doctor_recommended_first_aid.condition_trigger}) — Updated by{" "}
                {sosDispatchedData.doctor_recommended_first_aid.updated_by_doctor_id}:
              </p>
              <ul style={{ fontSize: "1.2rem", color: "#4ADE80" }}>
                {sosDispatchedData.doctor_recommended_first_aid.immediate_steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
              <p style={{ color: "#F87171", fontWeight: "bold" }}>
                ⚠️ DO NOT: {sosDispatchedData.doctor_recommended_first_aid.do_not_do}
              </p>
            </div>
          ) : (
            <p>No custom doctor first-aid configured yet. Keep patient calm until ambulance arrives.</p>
          )}
        </div>
      )}
    </section>
  );
}