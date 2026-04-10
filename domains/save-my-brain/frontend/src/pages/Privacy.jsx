import { useTranslation } from "../i18n";

export default function Privacy() {
  const { t } = useTranslation();

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-base)", padding: "40px 24px" }}>
      <div style={{ maxWidth: "700px", margin: "0 auto" }}>
        <a href="/" style={{ color: "var(--accent)", fontSize: "14px" }}>← {t("common.back")}</a>
        <h1 style={{ fontSize: "28px", fontWeight: 700, margin: "16px 0" }}>{t("nav.privacy")}</h1>

        <div className="card" style={{ padding: "32px", lineHeight: 1.8, fontSize: "14px" }}>
          <h2>Privacy Policy — Save My Brain AI</h2>
          <p><em>Last updated: April 2026</em></p>

          <h3>What we collect</h3>
          <p>When you use Save My Brain, we process documents you upload (photos, PDFs) to extract key information. We store:</p>
          <ul>
            <li>Document summaries and extracted data (dates, amounts, names)</li>
            <li>Your conversation history with the AI assistant</li>
            <li>Your profile information (name, language preference)</li>
          </ul>

          <h3>How we use your data</h3>
          <ul>
            <li>To provide document intelligence and life admin services</li>
            <li>To generate personalized daily briefs and reminders</li>
            <li>To improve the quality of document processing</li>
          </ul>

          <h3>Data storage</h3>
          <p>Your data is stored locally in structured context files. Documents are processed using AI (Claude by Anthropic) and the extracted information is stored — original files are not retained after processing.</p>

          <h3>Third-party services</h3>
          <ul>
            <li><strong>Anthropic (Claude AI)</strong> — document analysis and AI responses</li>
            <li><strong>Telegram</strong> — messaging interface</li>
            <li><strong>Stripe</strong> — payment processing (if applicable)</li>
          </ul>

          <h3>Your rights</h3>
          <p>You can request deletion of all your data at any time by contacting us or using the /reset command in Telegram.</p>

          <h3>Contact</h3>
          <p>For privacy inquiries: via the Telegram bot or your account settings.</p>
        </div>
      </div>
    </div>
  );
}
