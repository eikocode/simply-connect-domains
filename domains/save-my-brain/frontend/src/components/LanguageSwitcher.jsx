export default function LanguageSwitcher({ lang, setLang }) {
  const langs = [
    { code: "en", label: "EN" },
    { code: "zh-tw", label: "繁中" },
    { code: "ja", label: "日本語" },
  ];

  return (
    <div style={{ display: "flex", gap: "4px" }}>
      {langs.map((l) => (
        <button
          key={l.code}
          onClick={() => setLang(l.code)}
          className={`btn btn-sm ${lang === l.code ? "btn-primary" : "btn-ghost"}`}
          style={{ padding: "4px 10px", fontSize: "12px", borderRadius: "9999px" }}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}
