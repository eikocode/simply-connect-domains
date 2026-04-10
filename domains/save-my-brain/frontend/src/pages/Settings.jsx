import { useTranslation } from "../i18n";
import { getUser, logout } from "../auth";
import LanguageSwitcher from "../components/LanguageSwitcher";

export default function Settings() {
  const { t, lang, setLang } = useTranslation();
  const user = getUser();

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-base)" }}>
      <nav style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "12px 24px", borderBottom: "1px solid var(--border)",
      }}>
        <a href="/dashboard" style={{ fontWeight: 700, color: "inherit", textDecoration: "none" }}>
          🧠 {t("app.name")}
        </a>
        <button onClick={logout} className="btn btn-ghost btn-sm">{t("nav.logout")}</button>
      </nav>

      <div style={{ maxWidth: "600px", margin: "0 auto", padding: "24px" }}>
        <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "24px" }}>{t("settings.title")}</h1>

        {/* Profile */}
        <div className="card" style={{ padding: "24px", marginBottom: "16px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>{t("settings.profile")}</h2>
          <div style={{ marginBottom: "12px" }}>
            <label className="input-label">Name</label>
            <input className="input" value={user?.name || ""} readOnly style={{ width: "100%" }} />
          </div>
          <div>
            <label className="input-label">{t("settings.language")}</label>
            <LanguageSwitcher lang={lang} setLang={setLang} />
          </div>
        </div>

        {/* Connections */}
        <div className="card" style={{ padding: "24px", marginBottom: "16px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>{t("settings.connections")}</h2>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "24px" }}>💬</span>
            <span>{t("settings.telegram_connected")}</span>
            <a
              href="https://t.me/SaveMyBrainSC_bot"
              target="_blank"
              className="btn btn-outline btn-sm"
              style={{ marginLeft: "auto" }}
            >
              Open Bot
            </a>
          </div>
        </div>

        {/* Billing */}
        <div className="card" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>{t("settings.billing")}</h2>
          <p style={{ opacity: 0.6, fontSize: "14px" }}>
            Current plan: <strong>Trial</strong>
          </p>
          <button className="btn btn-primary" style={{ marginTop: "12px" }}>
            {t("settings.upgrade")}
          </button>
        </div>
      </div>
    </div>
  );
}
