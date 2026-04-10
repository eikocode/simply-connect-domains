import { useTranslation } from "../i18n";
import LanguageSwitcher from "../components/LanguageSwitcher";

export default function Landing() {
  const { t, lang, setLang } = useTranslation();

  return (
    <div className="landing">
      {/* Nav */}
      <nav className="landing-nav">
        <div className="landing-nav-inner">
          <span className="landing-logo">🧠 {t("app.name")}</span>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <LanguageSwitcher lang={lang} setLang={setLang} />
            <a href="/login" className="btn btn-ghost btn-sm">{t("nav.login")}</a>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="landing-hero">
        <div className="landing-hero-inner">
          <div className="landing-hero-text">
            <h1 className="landing-headline">{t("landing.hero_title")}</h1>
            <p className="landing-subheadline">{t("landing.hero_subtitle")}</p>
            <div style={{ display: "flex", gap: "12px", marginTop: "24px", flexWrap: "wrap" }}>
              <a
                href="https://t.me/SaveMyBrainSC_bot"
                target="_blank"
                rel="noopener"
                className="btn btn-primary btn-lg"
              >
                💬 {t("landing.cta_telegram")}
              </a>
              <a href="/login" className="btn btn-outline btn-lg">
                {t("landing.cta_login")}
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="landing-section">
        <h2 className="landing-section-title">{t("landing.features_title")}</h2>
        <p style={{ textAlign: "center", opacity: 0.6, marginBottom: "12px", fontSize: "13px" }}>
          {t("common.powered_by")}
        </p>
        <div className="landing-features-grid">
          {t("landing.features").map((f, i) => (
            <div key={i} className="card">
              <div style={{ fontSize: "32px", marginBottom: "12px" }}>{f.icon}</div>
              <h3 className="card-title">{f.title}</h3>
              <p className="card-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Personas */}
      <section className="landing-section" style={{ background: "var(--bg-surface)" }}>
        <h2 className="landing-section-title">{t("landing.personas_title")}</h2>
        <div className="landing-features-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
          {t("landing.personas").map((p, i) => (
            <div key={i} className="card" style={{ textAlign: "center" }}>
              <div style={{ fontSize: "40px", marginBottom: "8px" }}>{p.icon}</div>
              <h3 className="card-title" style={{ fontSize: "15px" }}>{p.title}</h3>
              <p className="card-desc" style={{ fontSize: "13px" }}>{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="landing-section">
        <h2 className="landing-section-title">{t("landing.pricing_title")}</h2>
        <div className="landing-features-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", maxWidth: "900px", margin: "0 auto" }}>
          {t("landing.pricing").map((plan, i) => (
            <div
              key={i}
              className="card"
              style={{
                border: plan.popular ? "2px solid var(--accent)" : undefined,
                position: "relative",
              }}
            >
              {plan.popular && (
                <span className="badge badge-accent" style={{ position: "absolute", top: "-12px", right: "16px" }}>
                  Popular
                </span>
              )}
              <h3 className="card-title">{plan.name}</h3>
              <div style={{ fontSize: "32px", fontWeight: 800, margin: "8px 0" }}>
                {plan.price}
                <span style={{ fontSize: "14px", fontWeight: 400, opacity: 0.6 }}> {plan.period}</span>
              </div>
              <ul style={{ listStyle: "none", padding: 0, margin: "16px 0" }}>
                {plan.features.map((f, j) => (
                  <li key={j} style={{ padding: "4px 0", fontSize: "14px" }}>✓ {f}</li>
                ))}
              </ul>
              <a
                href="https://t.me/SaveMyBrainSC_bot"
                className={`btn ${plan.popular ? "btn-primary" : "btn-outline"}`}
                style={{ width: "100%" }}
              >
                {t("landing.cta_telegram")}
              </a>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p style={{ opacity: 0.5, fontSize: "13px" }}>
          {t("common.powered_by")} · <a href="/privacy" style={{ color: "inherit" }}>{t("nav.privacy")}</a>
        </p>
      </footer>
    </div>
  );
}
