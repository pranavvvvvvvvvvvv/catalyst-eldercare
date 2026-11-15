import React from "react";
import { Languages, Mic, LogOut, ShieldCheck } from "lucide-react";

const ROLE_BADGES = {
  ELDER: { label: "👵 Elderly Patient Personal Portal", color: "#38BDF8" },
  DOCTOR: { label: "🩺 Verified Doctor Consultation Portal", color: "#FACC15" },
  CARETAKER: { label: "🫂 Family & Caretaker Monitoring Portal", color: "#4ADE80" },
};

export default function Header({
  title,
  currentUser,
  lang,
  onLanguageChange,
  voiceCommandsOn,
  onToggleVoiceCommand,
  highContrast,
  onToggleContrast,
  onLogout,
}) {
  const badge = ROLE_BADGES[currentUser.role] || ROLE_BADGES.ELDER;

  return (
    <header
      role="banner"
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "space-between",
        alignItems: "center",
        gap: "1rem",
        borderBottom: "2px solid #334155",
        paddingBottom: "1rem",
        marginBottom: "1.5rem",
      }}
    >
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
          <h1 style={{ fontSize: "1.75rem", margin: 0, color: "#38BDF8" }}>{title}</h1>
          <span
            style={{
              backgroundColor: "#1E293B",
              border: `2px solid ${badge.color}`,
              color: badge.color,
              padding: "0.3rem 0.8rem",
              borderRadius: "999px",
              fontSize: "0.9rem",
              fontWeight: "bold",
              display: "inline-flex",
              alignItems: "center",
              gap: "0.35rem",
            }}
          >
            <ShieldCheck size={16} /> {badge.label}
          </span>
        </div>
        <p style={{ margin: "0.35rem 0 0", fontSize: "0.95rem", opacity: 0.9 }}>
          Signed in as: <strong>{currentUser.name}</strong> ({currentUser.email})
        </p>
      </div>

      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
        {currentUser.role !== "DOCTOR" && (
          <>
            <Languages size={22} />
            {[
              { code: "mr", label: "मराठी" },
              { code: "hi", label: "हिन्दी" },
              { code: "en", label: "English" },
            ].map((l) => (
              <button
                key={l.code}
                onClick={() => onLanguageChange(l.code)}
                aria-pressed={lang === l.code}
                style={{
                  minHeight: "44px",
                  padding: "0.4rem 0.85rem",
                  fontWeight: "bold",
                  borderRadius: "8px",
                  border: "2px solid #38BDF8",
                  backgroundColor: lang === l.code ? "#38BDF8" : "transparent",
                  color: lang === l.code ? "#000" : "inherit",
                  cursor: "pointer",
                }}
              >
                {l.label}
              </button>
            ))}

            <button
              onClick={onToggleVoiceCommand}
              aria-label="Toggle Voice Command Listener"
              style={{
                minHeight: "44px",
                padding: "0.4rem 0.85rem",
                fontWeight: "bold",
                borderRadius: "8px",
                backgroundColor: voiceCommandsOn ? "#22C55E" : "#334155",
                color: "#FFF",
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "0.4rem",
              }}
            >
              <Mic size={18} /> {voiceCommandsOn ? "Listening ('Ambulance')..." : "Voice Trigger"}
            </button>
          </>
        )}

        <button
          onClick={onToggleContrast}
          style={{
            minHeight: "44px",
            padding: "0.4rem 0.85rem",
            borderRadius: "8px",
            border: "2px solid #94A3B8",
            background: "transparent",
            color: "inherit",
            cursor: "pointer",
          }}
        >
          {highContrast ? "Light Mode" : "High Contrast"}
        </button>

        <button
          onClick={onLogout}
          style={{
            minHeight: "44px",
            padding: "0.4rem 0.9rem",
            borderRadius: "8px",
            backgroundColor: "#EF4444",
            color: "#FFF",
            fontWeight: "bold",
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.35rem",
          }}
        >
          <LogOut size={16} /> Logout / Switch User
        </button>
      </div>
    </header>
  );
}