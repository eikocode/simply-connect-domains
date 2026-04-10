import { useState, useEffect } from "react";
import { useTranslation } from "../i18n";
import { getUser, logout } from "../auth";
import { listTasks, listExpiryDates, getFinancialSummary, listFamilyMembers, searchDocuments } from "../mcp";
import LanguageSwitcher from "../components/LanguageSwitcher";

export default function Dashboard() {
  const { t, lang, setLang } = useTranslation();
  const user = getUser();
  const [activeTab, setActiveTab] = useState("tasks");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadTab(activeTab);
  }, [activeTab]);

  async function loadTab(tab) {
    setLoading(true);
    setError(null);
    try {
      let result;
      switch (tab) {
        case "tasks": result = await listTasks("pending"); break;
        case "deadlines": result = await listExpiryDates(90); break;
        case "finances": result = await getFinancialSummary("this_month"); break;
        case "family": result = await listFamilyMembers(); break;
        case "documents": result = await searchDocuments("", null); break;
        default: result = {};
      }
      setData(result);
    } catch (e) {
      setError(e.message || t("common.error"));
    } finally {
      setLoading(false);
    }
  }

  const tabs = [
    { id: "tasks", icon: "✅", label: t("dashboard.tasks") },
    { id: "deadlines", icon: "📅", label: t("dashboard.deadlines") },
    { id: "finances", icon: "💰", label: t("dashboard.finances") },
    { id: "documents", icon: "🧾", label: t("dashboard.documents") },
    { id: "family", icon: "👨‍👩‍👧‍👦", label: t("dashboard.family") },
  ];

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-base)" }}>
      {/* Top bar */}
      <nav style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "12px 24px", borderBottom: "1px solid var(--border-light)",
      }}>
        <span style={{ fontWeight: 700 }}>🧠 {t("app.name")}</span>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <LanguageSwitcher lang={lang} setLang={setLang} />
          <a href="/settings" className="btn btn-ghost btn-sm">{t("nav.settings")}</a>
          <button onClick={logout} className="btn btn-ghost btn-sm">{t("nav.logout")}</button>
        </div>
      </nav>

      <div style={{ maxWidth: "900px", margin: "0 auto", padding: "24px" }}>
        {/* Welcome */}
        <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "24px" }}>
          {t("dashboard.welcome")}, {user?.name || "User"} 👋
        </h1>

        {/* Tabs */}
        <div style={{ display: "flex", gap: "8px", marginBottom: "24px", flexWrap: "wrap" }}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`btn btn-sm ${activeTab === tab.id ? "btn-primary" : "btn-outline"}`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="card" style={{ padding: "24px" }}>
          {loading ? (
            <p style={{ opacity: 0.5 }}>{t("common.loading")}</p>
          ) : error ? (
            <div>
              <p style={{ color: "var(--danger)" }}>{error}</p>
              <p style={{ opacity: 0.5, fontSize: "13px", marginTop: "8px" }}>
                Make sure the MCP server is running (sc-mcp)
              </p>
            </div>
          ) : (
            <TabContent tab={activeTab} data={data} t={t} />
          )}
        </div>

        {/* Telegram CTA */}
        <div style={{ textAlign: "center", marginTop: "32px", opacity: 0.6, fontSize: "13px" }}>
          <p>💬 {t("dashboard.upload_hint")}: <a href="https://t.me/SaveMyBrainSC_bot" target="_blank" style={{ color: "var(--accent)" }}>@SaveMyBrainSC_bot</a></p>
        </div>
      </div>
    </div>
  );
}

function TabContent({ tab, data, t }) {
  if (!data) return null;

  switch (tab) {
    case "tasks":
      return data.count === 0 ? (
        <p style={{ opacity: 0.5 }}>{t("dashboard.no_tasks")}</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {data.tasks?.map((task, i) => (
            <li key={i} style={{ padding: "8px 0", borderBottom: "1px solid var(--border-light)" }}>
              <span className={`badge badge-${task.priority === "P1" ? "danger" : task.priority === "P2" ? "warning" : "info"}`} style={{ marginRight: "8px" }}>
                {task.priority}
              </span>
              {task.description}
            </li>
          ))}
        </ul>
      );

    case "deadlines":
      return data.count === 0 ? (
        <p style={{ opacity: 0.5 }}>{t("dashboard.no_deadlines")}</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {data.dates?.map((d, i) => (
            <li key={i} style={{ padding: "8px 0", borderBottom: "1px solid var(--border-light)" }}>
              <span className={`badge badge-${d.priority === "P1" ? "danger" : d.priority === "P2" ? "warning" : "info"}`} style={{ marginRight: "8px" }}>
                {d.days_until}d
              </span>
              <strong>{d.date}</strong> — {d.label}
            </li>
          ))}
        </ul>
      );

    case "finances":
      return data.total === 0 && Object.keys(data.by_category || {}).length === 0 ? (
        <p style={{ opacity: 0.5 }}>{t("dashboard.no_finances")}</p>
      ) : (
        <div>
          <h3 style={{ fontSize: "18px", marginBottom: "16px" }}>
            {data.period} — Total: ${Math.abs(data.total || 0).toFixed(2)}
          </h3>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {Object.entries(data.by_category || {}).map(([cat, amount]) => (
              <li key={cat} style={{ padding: "6px 0", display: "flex", justifyContent: "space-between" }}>
                <span style={{ textTransform: "capitalize" }}>{cat}</span>
                <span style={{ fontWeight: 600 }}>${Math.abs(amount).toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </div>
      );

    case "documents":
      return data.count === 0 ? (
        <p style={{ opacity: 0.5 }}>{t("dashboard.no_documents")}</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {data.matches?.map((doc, i) => (
            <li key={i} className="card" style={{ padding: "12px", marginBottom: "8px" }}>
              <strong>{doc.title}</strong>
              <p style={{ fontSize: "13px", opacity: 0.7, marginTop: "4px" }}>{doc.excerpt}</p>
            </li>
          ))}
        </ul>
      );

    case "family":
      return data.count === 0 ? (
        <p style={{ opacity: 0.5 }}>{t("dashboard.no_family")}</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {data.members?.map((m, i) => (
            <li key={i} style={{ padding: "8px 0", borderBottom: "1px solid var(--border-light)" }}>
              👤 <strong>{m.name}</strong> {m.relationship && <span style={{ opacity: 0.5 }}>({m.relationship})</span>}
            </li>
          ))}
        </ul>
      );

    default:
      return null;
  }
}
