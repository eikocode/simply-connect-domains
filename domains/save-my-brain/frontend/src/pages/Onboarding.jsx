/**
 * Onboarding.jsx — 3-step simplified onboarding
 *
 * Steps:
 *   1. Consent
 *   2. Household mode (Just me / Me + family)
 *   3. Family names (if Me + family) — names only, max 7
 *   4. Completion → redirect to /dashboard
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "../i18n";
import { getUser, login } from "../auth";
import LanguageSwitcher from "../components/LanguageSwitcher";

const MAX_FAMILY_MEMBERS = 7;

export default function Onboarding() {
  const { t, lang, setLang } = useTranslation();
  const navigate = useNavigate();
  const user = getUser();

  const [step, setStep] = useState("consent"); // consent | household | family | complete
  const [householdMode, setHouseholdMode] = useState(null);
  const [familyText, setFamilyText] = useState("");
  const [familyNames, setFamilyNames] = useState([]);
  const [familyError, setFamilyError] = useState("");

  // Example names per language (one per line — web supports newlines)
  const exampleNames = {
    en: "John\nMary",
    "zh-tw": "大明\n美美",
    ja: "三郎\n雅美",
  };

  function handleConsent(agreed) {
    if (agreed) {
      setStep("household");
    } else {
      navigate("/");
    }
  }

  function handleHousehold(mode) {
    setHouseholdMode(mode);
    if (mode === "solo") {
      completeOnboarding([]);
    } else {
      setStep("family");
    }
  }

  function parseNames(text) {
    // Split on newline, comma (EN/CN), Japanese mark, ampersand,
    // and conjunctions: "and", "及", "と"
    return text
      .split(/[\n,，、&]|\s+and\s+|\s+及\s+|\s*と\s*/i)
      .map((n) => n.trim())
      .filter((n) => n && n.length < 60);
  }

  function dedupNames(names) {
    // Case-insensitive dedup, preserving first-seen order.
    // Returns { unique: [...], duplicates: [...] }
    const seen = new Set();
    const unique = [];
    const duplicates = [];
    for (const name of names) {
      const key = name.toLowerCase();
      if (seen.has(key)) {
        duplicates.push(name);
      } else {
        seen.add(key);
        unique.push(name);
      }
    }
    return { unique, duplicates };
  }

  function handleFamilySubmit(e) {
    e.preventDefault();
    setFamilyError("");

    const raw = parseNames(familyText);
    const { unique, duplicates } = dedupNames(raw);

    // REJECT if too many (after dedup) — show warning, don't advance
    if (unique.length > MAX_FAMILY_MEMBERS) {
      setFamilyError(
        t("onboarding.family_too_many").replace("{count}", unique.length)
      );
      return;
    }

    // If there were duplicates, surface them (but still proceed)
    if (duplicates.length > 0) {
      const dupNote = t("onboarding.family_dup_note")
        .replace("{dups}", duplicates.join(", "));
      // Show as info, not error — still proceed
      alert(dupNote);
    }

    setFamilyNames(unique);
    completeOnboarding(unique);
  }

  function completeOnboarding(names) {
    // Mark onboarding as complete in localStorage
    const updatedUser = { ...user, onboarding_complete: true, family: names };
    login(localStorage.getItem("smb_token") || "user", updatedUser);
    setStep("complete");
    setTimeout(() => navigate("/dashboard"), 2000);
  }

  const wrapperStyle = {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "var(--bg-surface)",
    padding: "20px",
  };

  const cardStyle = {
    maxWidth: "480px",
    width: "100%",
    padding: "40px",
  };

  return (
    <div style={wrapperStyle}>
      <div className="card" style={cardStyle}>
        {/* Language switcher */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "16px" }}>
          <LanguageSwitcher lang={lang} setLang={setLang} />
        </div>

        {step === "consent" && <ConsentStep t={t} user={user} onConsent={handleConsent} />}
        {step === "household" && <HouseholdStep t={t} onPick={handleHousehold} />}
        {step === "family" && (
          <FamilyStep
            t={t}
            lang={lang}
            exampleNames={exampleNames[lang] || exampleNames.en}
            familyText={familyText}
            setFamilyText={setFamilyText}
            onSubmit={handleFamilySubmit}
            error={familyError}
          />
        )}
        {step === "complete" && <CompleteStep t={t} />}
      </div>
    </div>
  );
}

function ConsentStep({ t, user, onConsent }) {
  const name = user?.name ? ` ${user.name}` : "";
  return (
    <div>
      <div style={{ textAlign: "center", marginBottom: "24px" }}>
        <div style={{ fontSize: "56px", marginBottom: "8px" }}>🧠</div>
        <h1 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "4px" }}>
          {t("onboarding.consent_title")}{name}! 👋
        </h1>
      </div>

      <p style={{ fontSize: "15px", lineHeight: 1.6, marginBottom: "16px", color: "var(--text-secondary)" }}>
        {t("onboarding.consent_intro")}
      </p>

      <div style={{ padding: "12px 16px", background: "var(--bg-surface)", borderRadius: "var(--radius-sm)", marginBottom: "24px" }}>
        <div style={{ fontSize: "13px", fontWeight: 600, marginBottom: "4px" }}>🔒 {t("onboarding.privacy_title")}</div>
        <div style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
          {t("onboarding.privacy_body")}
        </div>
      </div>

      <button onClick={() => onConsent(true)} className="btn btn-brand btn-lg" style={{ width: "100%", marginBottom: "8px" }}>
        ✓ {t("onboarding.consent_agree")}
      </button>
      <button onClick={() => onConsent(false)} className="btn btn-ghost" style={{ width: "100%" }}>
        {t("onboarding.consent_decline")}
      </button>
    </div>
  );
}

function HouseholdStep({ t, onPick }) {
  return (
    <div>
      <div style={{ textAlign: "center", marginBottom: "24px" }}>
        <div style={{ fontSize: "56px", marginBottom: "8px" }}>👨‍👩‍👧‍👦</div>
        <h1 style={{ fontSize: "22px", fontWeight: 700 }}>
          {t("onboarding.household_title")}
        </h1>
      </div>

      <button
        onClick={() => onPick("solo")}
        className="btn btn-outline btn-lg"
        style={{ width: "100%", marginBottom: "12px", justifyContent: "flex-start", padding: "20px" }}
      >
        <span style={{ fontSize: "24px", marginRight: "12px" }}>👤</span>
        <span>{t("onboarding.household_solo")}</span>
      </button>

      <button
        onClick={() => onPick("family")}
        className="btn btn-outline btn-lg"
        style={{ width: "100%", justifyContent: "flex-start", padding: "20px" }}
      >
        <span style={{ fontSize: "24px", marginRight: "12px" }}>👨‍👩‍👧‍👦</span>
        <span>{t("onboarding.household_family")}</span>
      </button>
    </div>
  );
}

function FamilyStep({ t, lang, exampleNames, familyText, setFamilyText, onSubmit, error }) {
  // Live parse with the same logic as the submit handler
  const parsedNames = familyText
    .split(/[\n,，、&]|\s+and\s+|\s+及\s+|\s*と\s*/i)
    .map((n) => n.trim())
    .filter((n) => n && n.length < 60);

  const currentCount = parsedNames.length;
  const overLimit = currentCount > 7;
  const showWarning = overLimit || !!error;

  return (
    <form onSubmit={onSubmit}>
      <div style={{ textAlign: "center", marginBottom: "24px" }}>
        <div style={{ fontSize: "56px", marginBottom: "8px" }}>👥</div>
        <h1 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "8px" }}>
          {t("onboarding.family_title")}
        </h1>
        <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
          {t("onboarding.family_hint")}
        </p>
      </div>

      <label className="input-label" style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <span>{t("onboarding.family_label")}</span>
        <span style={{
          fontWeight: 600,
          fontSize: "13px",
          color: overLimit ? "var(--danger)" : "var(--text-secondary)",
          textTransform: "none",
          letterSpacing: "0",
        }}>
          {currentCount}/7
        </span>
      </label>
      <textarea
        className="input"
        rows={6}
        placeholder={exampleNames}
        value={familyText}
        onChange={(e) => setFamilyText(e.target.value)}
        style={{
          width: "100%",
          marginBottom: "8px",
          fontFamily: "var(--font-family)",
          fontSize: "15px",
          resize: "vertical",
          borderColor: overLimit ? "var(--danger)" : undefined,
        }}
      />

      {showWarning && (
        <div style={{
          padding: "12px 16px",
          background: "#fef2f2",
          border: "1px solid var(--danger)",
          borderRadius: "var(--radius-sm)",
          color: "var(--danger)",
          fontSize: "14px",
          fontWeight: 500,
          marginBottom: "12px",
          lineHeight: 1.5,
        }}>
          ⚠️ {t("onboarding.family_too_many").replace("{count}", currentCount)}
        </div>
      )}

      <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "20px" }}>
        {t("onboarding.family_note")}
      </p>

      <button
        type="submit"
        className="btn btn-brand btn-lg"
        style={{ width: "100%", opacity: overLimit ? 0.5 : 1 }}
        disabled={overLimit}
      >
        {t("onboarding.family_continue")}
      </button>
    </form>
  );
}

function CompleteStep({ t }) {
  return (
    <div style={{ textAlign: "center", padding: "20px 0" }}>
      <div style={{ fontSize: "72px", marginBottom: "16px" }}>🎉</div>
      <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "8px" }}>
        {t("onboarding.complete_title")}
      </h1>
      <p style={{ fontSize: "15px", color: "var(--text-secondary)", lineHeight: 1.6 }}>
        {t("onboarding.complete_body")}
      </p>
      <p style={{ fontSize: "13px", color: "var(--text-tertiary)", marginTop: "24px" }}>
        {t("onboarding.complete_redirect")}
      </p>
    </div>
  );
}
