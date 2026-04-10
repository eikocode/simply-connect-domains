/**
 * Landing.jsx — Save My Brain AI (Airbnb-inspired)
 *
 * Two-column hero (headline+QR left, steps right)
 * + Features + Personas + Pricing + Bottom CTA
 */

import { useEffect, useRef } from "react";
import { useTranslation } from "../i18n";
import LanguageSwitcher from "../components/LanguageSwitcher";

const BOT_URL = "https://t.me/SaveMyBrainSC_bot";

function useScrollReveal() {
  const ref = useRef(null);
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) e.target.classList.add("visible"); }),
      { threshold: 0.1 }
    );
    ref.current?.querySelectorAll(".animate-on-scroll").forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);
  return ref;
}

export default function Landing() {
  const { t, lang, setLang } = useTranslation();
  const revealRef = useScrollReveal();

  return (
    <div ref={revealRef}>
      {/* ── Nav ─────────────────────────── */}
      <nav className="landing-nav">
        <div className="landing-nav-inner">
          <span className="landing-logo">🧠 Save My Brain</span>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <LanguageSwitcher lang={lang} setLang={setLang} />
            <a href="/login" className="btn btn-outline btn-sm">{t("nav.login")}</a>
          </div>
        </div>
      </nav>

      {/* ── Hero (two-column) ──────────── */}
      <section style={{ padding: "64px 24px 48px", maxWidth: "1100px", margin: "0 auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "48px", alignItems: "start" }}>

          {/* Left: headline + QR */}
          <div>
            <div style={{
              display: "inline-block", padding: "4px 14px", borderRadius: "var(--radius-full)",
              background: "var(--brand-light)", color: "var(--brand)", fontSize: "13px",
              fontWeight: "var(--fw-semibold)", marginBottom: "20px",
            }}>
              {t("landing.pill")}
            </div>

            <h1 style={{
              fontSize: "clamp(28px, 4vw, 44px)", fontWeight: "var(--fw-bold)",
              lineHeight: 1.15, letterSpacing: "-0.44px", marginBottom: "16px",
            }}>
              {t("landing.hero_title")}
            </h1>

            <p style={{ fontSize: "16px", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "8px" }}>
              {t("landing.hero_subtitle")}
            </p>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "32px" }}>
              {t("landing.hero_sub")}
            </p>

            {/* Phone + QR row */}
            <div style={{ display: "flex", gap: "24px", alignItems: "flex-end" }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: "64px", marginBottom: "8px" }}>📱</div>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)", whiteSpace: "pre-line", lineHeight: 1.4 }}>
                  {t("landing.phone_caption")}
                </p>
              </div>

              <div className="card" style={{ padding: "20px", textAlign: "center", minWidth: "160px" }}>
                <div style={{ fontSize: "10px", fontWeight: "var(--fw-bold)", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-secondary)", marginBottom: "8px" }}>
                  TELEGRAM
                </div>
                <img src="/qr-telegram.png" alt="Telegram QR code" style={{ width: "120px", height: "120px", margin: "0 auto 12px", borderRadius: "var(--radius-sm)" }} />
                <div style={{ fontSize: "12px", fontWeight: "var(--fw-semibold)", letterSpacing: "-0.18px" }}>
                  save your brain
                </div>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "8px" }}>
                  📱 {t("landing.qr_label")}
                </p>
              </div>
            </div>
          </div>

          {/* Right: CTA + steps + social proof */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <a href={BOT_URL} target="_blank" rel="noopener" className="btn btn-brand btn-lg" style={{ alignSelf: "flex-start" }}>
              ✈️ {t("landing.cta_telegram")}
            </a>

            {t("landing.steps").map((step, i) => (
              <div key={i} className="card" style={{ padding: "20px", display: "flex", gap: "16px", alignItems: "flex-start" }}>
                <div style={{
                  width: "32px", height: "32px", borderRadius: "50%", background: "var(--brand-light)",
                  color: "var(--brand)", display: "flex", alignItems: "center", justifyContent: "center",
                  fontWeight: "var(--fw-bold)", fontSize: "14px", flexShrink: 0,
                }}>
                  {i + 1}
                </div>
                <div>
                  <h3 style={{ fontSize: "15px", fontWeight: "var(--fw-semibold)", marginBottom: "4px" }}>
                    {step.title}
                  </h3>
                  <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.43 }}>
                    {step.desc}
                  </p>
                </div>
              </div>
            ))}

            {/* Social proof */}
            <div className="card" style={{ padding: "20px", background: "var(--bg-surface)" }}>
              <div style={{ fontSize: "11px", fontWeight: "var(--fw-bold)", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--success)", marginBottom: "4px" }}>
                {t("landing.secure_label")}
              </div>
              <div style={{ fontWeight: "var(--fw-semibold)", fontSize: "15px" }}>
                {t("landing.social_proof")}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ───────────────────── */}
      <section className="landing-section">
        <h2 className="landing-section-title animate-on-scroll">{t("landing.features_title")}</h2>
        <p style={{ textAlign: "center", color: "var(--text-secondary)", marginBottom: "12px", fontSize: "13px" }}>
          {t("common.powered_by")}
        </p>
        <div className="landing-features-grid">
          {t("landing.features").map((f, i) => (
            <div key={i} className="card animate-on-scroll">
              <div style={{ fontSize: "32px", marginBottom: "12px" }}>{f.icon}</div>
              <h3 className="card-title">{f.title}</h3>
              <p className="card-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Personas ───────────────────── */}
      <section className="landing-section" style={{ background: "var(--bg-surface)" }}>
        <h2 className="landing-section-title animate-on-scroll">{t("landing.personas_title")}</h2>
        <div className="landing-features-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
          {t("landing.personas").map((p, i) => (
            <div key={i} className="card animate-on-scroll" style={{ textAlign: "center" }}>
              <div style={{ fontSize: "40px", marginBottom: "8px" }}>{p.icon}</div>
              <h3 className="card-title" style={{ fontSize: "15px" }}>{p.title}</h3>
              <p className="card-desc" style={{ fontSize: "13px" }}>{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Pricing ────────────────────── */}
      <section className="landing-section">
        <h2 className="landing-section-title animate-on-scroll">{t("landing.pricing_title")}</h2>
        <div className="landing-features-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", maxWidth: "900px", margin: "0 auto" }}>
          {t("landing.pricing").map((plan, i) => (
            <div key={i} className="card animate-on-scroll" style={{
              border: plan.popular ? "2px solid var(--brand)" : undefined,
              position: "relative",
            }}>
              {plan.popular && (
                <span className="badge badge-accent" style={{ position: "absolute", top: "-12px", right: "16px" }}>Popular</span>
              )}
              <h3 className="card-title">{plan.name}</h3>
              <div style={{ fontSize: "32px", fontWeight: "var(--fw-bold)", margin: "8px 0" }}>
                {plan.price}
                <span style={{ fontSize: "14px", fontWeight: "var(--fw-regular)", color: "var(--text-secondary)" }}> {plan.period}</span>
              </div>
              <ul style={{ listStyle: "none", padding: 0, margin: "16px 0" }}>
                {plan.features.map((f, j) => (
                  <li key={j} style={{ padding: "4px 0", fontSize: "14px" }}>✓ {f}</li>
                ))}
              </ul>
              <a href={BOT_URL} target="_blank" rel="noopener"
                className={`btn ${plan.popular ? "btn-brand" : "btn-outline"}`}
                style={{ width: "100%", textAlign: "center" }}>
                {t("landing.cta_telegram")}
              </a>
            </div>
          ))}
        </div>
      </section>

      {/* ── Bottom CTA ─────────────────── */}
      <section style={{ padding: "64px 24px", textAlign: "center", background: "var(--bg-surface)" }}>
        <h2 className="animate-on-scroll" style={{ fontSize: "28px", fontWeight: "var(--fw-bold)", marginBottom: "12px", letterSpacing: "-0.18px" }}>
          {t("landing.bottom_headline")}
        </h2>
        <p className="animate-on-scroll" style={{ color: "var(--text-secondary)", marginBottom: "24px", fontSize: "16px" }}>
          {t("landing.bottom_sub")}
        </p>
        <div className="animate-on-scroll">
          <a href={BOT_URL} target="_blank" rel="noopener" className="btn btn-brand btn-lg">
            ✈️ {t("landing.cta_telegram")}
          </a>
        </div>
      </section>

      {/* ── Footer ─────────────────────── */}
      <footer className="landing-footer">
        <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
          {t("common.powered_by")}
        </p>
        <div style={{ margin: "12px 0", fontWeight: "var(--fw-semibold)" }}>🧠 Santo Star Limited</div>
        <div style={{ display: "flex", justifyContent: "center", gap: "20px", marginBottom: "12px", fontSize: "14px" }}>
          <a href="/privacy">{t("nav.privacy")}</a>
          <a href={BOT_URL} target="_blank" rel="noopener">Telegram Bot</a>
        </div>
        <div style={{ fontSize: "13px", color: "var(--text-tertiary)" }}>
          &copy; {new Date().getFullYear()} Santo Star Limited
        </div>
      </footer>
    </div>
  );
}
