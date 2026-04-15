import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "../i18n";
import { login } from "../auth";
import LanguageSwitcher from "../components/LanguageSwitcher";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8091";
const POLL_INTERVAL_MS = 2000;
const CODE_TTL_MS = 10 * 60 * 1000; // 10 minutes

export default function Login() {
  const { t, lang, setLang } = useTranslation();
  const navigate = useNavigate();

  const [step, setStep]     = useState("idle");   // "idle" | "polling" | "done" | "error"
  const [code, setCode]     = useState("");
  const [errMsg, setErrMsg] = useState("");
  const pollTimer   = useRef(null);
  const expireTimer = useRef(null);

  function stopPolling() {
    if (pollTimer.current)   clearInterval(pollTimer.current);
    if (expireTimer.current) clearTimeout(expireTimer.current);
  }

  useEffect(() => () => stopPolling(), []);

  async function handleRequestCode() {
    setErrMsg("");
    try {
      const resp = await fetch(`${API_URL}/api/auth/request-code`, { method: "POST" });
      if (!resp.ok) throw new Error(`Server error (${resp.status})`);
      const data = await resp.json();
      setCode(data.code);
      setStep("polling");
      startPolling(data.code);
      expireTimer.current = setTimeout(() => {
        stopPolling();
        setStep("idle");
        setCode("");
        setErrMsg("Code expired — please try again.");
      }, CODE_TTL_MS);
    } catch (err) {
      setErrMsg("Could not reach the server. Please check your connection.");
    }
  }

  function startPolling(pairingCode) {
    pollTimer.current = setInterval(async () => {
      try {
        const resp = await fetch(
          `${API_URL}/api/auth/poll?code=${encodeURIComponent(pairingCode)}`
        );
        if (!resp.ok) return;
        const data = await resp.json();
        if (data.status === "complete") {
          stopPolling();
          login(data.token, data.user);
          setStep("done");
          setTimeout(() => {
            navigate(data.user.onboarding_complete ? "/dashboard" : "/onboarding");
          }, 1200);
        }
      } catch {
        // Network blip — keep polling
      }
    }, POLL_INTERVAL_MS);
  }

  // --- Render ---

  if (step === "done") {
    return (
      <div style={centreStyle}>
        <div className="card" style={cardStyle}>
          <div style={{ textAlign: "center", fontSize: "48px" }}>✅</div>
          <p style={{ textAlign: "center", marginTop: "12px", fontWeight: 600 }}>
            Connected! Redirecting…
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={centreStyle}>
      <div className="card" style={cardStyle}>

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <div style={{ fontSize: "48px", marginBottom: "8px" }}>🧠</div>
          <h1 style={{ fontSize: "24px", fontWeight: 700 }}>{t("app.name")}</h1>
          <p style={{ opacity: 0.6, fontSize: "14px" }}>{t("app.tagline")}</p>
        </div>

        {/* Idle: connect button */}
        {step === "idle" && (
          <>
            <button
              className="btn btn-primary"
              style={{ width: "100%" }}
              onClick={handleRequestCode}
            >
              🔗 Connect via Telegram
            </button>

            <div style={{ textAlign: "center", margin: "16px 0 8px", opacity: 0.4, fontSize: "12px" }}>
              — or open Telegram directly —
            </div>

            <a
              href="https://t.me/SaveMyBrainSC_bot"
              target="_blank"
              rel="noopener"
              className="btn btn-outline"
              style={{ width: "100%", textAlign: "center" }}
            >
              💬 {t("landing.cta_telegram")}
            </a>
          </>
        )}

        {/* Polling: show code */}
        {step === "polling" && (
          <div style={{ textAlign: "center" }}>
            <p style={{ opacity: 0.7, fontSize: "14px", marginBottom: "16px" }}>
              Open Telegram and send this code to{" "}
              <strong>@SaveMyBrainSC_bot</strong>:
            </p>

            <div style={{
              fontSize: "32px",
              fontWeight: 700,
              letterSpacing: "4px",
              padding: "16px",
              background: "var(--bg-surface, #f5f5f5)",
              borderRadius: "8px",
              marginBottom: "16px",
              fontFamily: "monospace",
              userSelect: "all",
            }}>
              {code}
            </div>

            <p style={{ opacity: 0.5, fontSize: "12px", marginBottom: "20px" }}>
              Waiting for confirmation… (valid for 10 minutes)
            </p>

            <button
              className="btn btn-outline"
              style={{ width: "100%" }}
              onClick={() => { stopPolling(); setStep("idle"); setCode(""); setErrMsg(""); }}
            >
              Cancel
            </button>
          </div>
        )}

        {/* Error message */}
        {errMsg && (
          <p style={{
            color: "var(--danger, #e74c3c)",
            fontSize: "13px",
            textAlign: "center",
            marginTop: "12px",
          }}>
            {errMsg}
          </p>
        )}

        <div style={{ display: "flex", justifyContent: "center", marginTop: "20px" }}>
          <LanguageSwitcher lang={lang} setLang={setLang} />
        </div>
      </div>
    </div>
  );
}

const centreStyle = {
  minHeight: "100vh",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "var(--bg-surface)",
  padding: "20px",
};

const cardStyle = {
  maxWidth: "400px",
  width: "100%",
  padding: "32px",
};
