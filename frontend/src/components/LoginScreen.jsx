import React, { useState } from "react";
import { GoogleLogin } from "@react-oauth/google";
import { jwtDecode } from "jwt-decode";
import { ShieldCheck } from "lucide-react";

export default function LoginScreen({ onLogin }) {
  const [selectedRole, setSelectedRole] = useState("ELDER");
  const [customEmail, setCustomEmail] = useState("shivam.eldercare@gmail.com");

  const handleGoogleSuccess = (credentialResponse) => {
    const decoded = jwtDecode(credentialResponse.credential);
    onLogin({
      email: decoded.email,
      name: decoded.name,
      role: selectedRole,
      google_token: credentialResponse.credential,
    });
  };

  const handleInstantRoleLogin = (e) => {
    e.preventDefault();
    const roleNames = {
      ELDER: "Ramesh Deshmukh (Senior)",
      CARETAKER: "Shivam (Caretaker)",
      DOCTOR: "Dr. Kulkarni",
    };
    onLogin({
      email: customEmail,
      name: roleNames[selectedRole],
      role: selectedRole,
      google_token: "demo-oauth-token",
    });
  };

  return (
    <main
      role="main"
      aria-label="Authentication Portal"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        backgroundColor: "#090D16",
        color: "#FFF",
        padding: "1.5rem",
      }}
    >
      <div
        style={{
          backgroundColor: "#1E293B",
          padding: "2.5rem",
          borderRadius: "14px",
          border: "2px solid #38BDF8",
          maxWidth: "460px",
          width: "100%",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.5rem" }}>
          <ShieldCheck size={32} color="#38BDF8" />
          <h1 style={{ color: "#38BDF8", margin: 0, fontSize: "1.75rem" }}>Catalyst ElderCare</h1>
        </div>
        <p style={{ color: "#94A3B8", marginBottom: "1.5rem" }}>
          Select your role to sign in with Google OAuth 2.0
        </p>

        {/* Role Selector */}
        <div style={{ display: "grid", gap: "0.75rem", marginBottom: "1.5rem" }}>
          {[
            { id: "ELDER", label: "👵 Elderly Patient Portal" },
            { id: "DOCTOR", label: "🩺 Medical Doctor Portal" },
            { id: "CARETAKER", label: "🫂 Family Caretaker Portal" },
          ].map((role) => (
            <label
              key={role.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.85rem",
                padding: "0.9rem 1rem",
                border: selectedRole === role.id ? "2px solid #FACC15" : "2px solid #475569",
                borderRadius: "8px",
                cursor: "pointer",
                backgroundColor: selectedRole === role.id ? "#0F172A" : "transparent",
              }}
            >
              <input
                type="radio"
                name="role"
                value={role.id}
                checked={selectedRole === role.id}
                onChange={(e) => setSelectedRole(e.target.value)}
                style={{ transform: "scale(1.4)" }}
              />
              <span style={{ fontSize: "1.1rem", fontWeight: "bold" }}>{role.label}</span>
            </label>
          ))}
        </div>

        {/* Official Google OAuth Button */}
        <div style={{ display: "flex", justifyContent: "center", marginBottom: "1.25rem" }}>
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => console.log("Google Login Failed")}
            theme="filled_blue"
            shape="pill"
          />
        </div>

        <hr style={{ borderColor: "#334155", margin: "1.25rem 0" }} />

        {/* Fast Local Evaluator Login */}
        <form onSubmit={handleInstantRoleLogin} style={{ display: "grid", gap: "0.6rem" }}>
          <label style={{ fontSize: "0.9rem", color: "#CBD5E1" }}>
            Notification Email (for Appointment & Course Updates):
            <input
              type="email"
              value={customEmail}
              onChange={(e) => setCustomEmail(e.target.value)}
              required
              style={{
                width: "100%",
                padding: "0.6rem",
                marginTop: "0.3rem",
                borderRadius: "6px",
                border: "1px solid #475569",
              }}
            />
          </label>
          <button
            type="submit"
            style={{
              minHeight: "48px",
              backgroundColor: "#38BDF8",
              color: "#000",
              fontWeight: "bold",
              fontSize: "1rem",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
            }}
          >
            Continue as {selectedRole}
          </button>
        </form>
      </div>
    </main>
  );
}