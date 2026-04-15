import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "../i18n";
import { login } from "../auth";
import LanguageSwitcher from "../components/LanguageSwitcher";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8090";

export default function Login() {
  const { t, lang, setLang } = useTranslation();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();

    // Require a name — the name becomes the user_id used throughout the app
    const trimmedName = name.trim();
    if (!trimmedName) {
      return;
    }

    setLoading(true);

    // Check whether THIS specific user (keyed by their display name) has
    // already completed onboarding on this deployment. Per-user, not global.
    let onboardingDone = false;
    try {
      const resp = await fetch(
        `${API_URL}/onboarding/status?user_id=${encodeURIComponent(trimmedName)}`
      );
      if (resp.ok) {
        const data = await resp.json();
        onboardingDone = !!data.completed;
      }
    } catch (err) {
      // API unreachable — proceed to onboarding as fallback
      console.warn("onboarding_status check failed:", err);
    }

    login(trimmedName, {
      name: trimmedName,
      lang,
      onboarding_complete: onboardingDone,
    });

    setLoading(false);
    navigate(onboardingDone ? "/dashboard" : "/onboarding");
  }

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "var(--bg-surface)",
      padding: "20px",
    }}>
      <div className="card" style={{ maxWidth: "400px", width: "100%", padding: "32px" }}>
        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <div style={{ fontSize: "48px", marginBottom: "8px" }}>🧠</div>
          <h1 style={{ fontSize: "24px", fontWeight: 700 }}>{t("app.name")}</h1>
          <p style={{ opacity: 0.6, fontSize: "14px" }}>{t("app.tagline")}</p>
        </div>

        <form onSubmit={handleSubmit}>
          <label className="input-label">{t("settings.profile")}</label>
          <input
            type="text"
            className="input"
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ width: "100%", marginBottom: "16px" }}
          />

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", opacity: loading ? 0.6 : 1 }}
            disabled={loading}
          >
            {loading ? (t("common.loading") || "…") : t("nav.login")}
          </button>
        </form>

        <div style={{ textAlign: "center", margin: "20px 0 12px", opacity: 0.4, fontSize: "12px" }}>
          — or —
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

        <div style={{ display: "flex", justifyContent: "center", marginTop: "20px" }}>
          <LanguageSwitcher lang={lang} setLang={setLang} />
        </div>
      </div>
    </div>
  );
}
