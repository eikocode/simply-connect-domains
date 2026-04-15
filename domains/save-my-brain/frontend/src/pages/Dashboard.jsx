import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "../i18n";
import { getUser, logout, getAuthHeaders } from "../auth";
import {
  listTasks,
  listExpiryDates,
  getFinancialSummary,
  listFamilyMembers,
  searchDocuments,
} from "../mcp";
import LanguageSwitcher from "../components/LanguageSwitcher";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8091";
const UPLOAD_URL = import.meta.env.VITE_UPLOAD_URL || API_URL;  // browser POSTs directly to tunnel
const UPLOAD_TOKEN = import.meta.env.VITE_UPLOAD_TOKEN || "";

export default function Dashboard() {
  const { t, lang, setLang } = useTranslation();
  const user = getUser();
  const navigate = useNavigate();

  // Chat state
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const chatEndRef = useRef(null);

  // Tabs state
  const [activeTab, setActiveTab] = useState("tasks");
  const [tabData, setTabData] = useState(null);
  const [tabLoading, setTabLoading] = useState(false);
  const [tabError, setTabError] = useState(null);

  // Upload
  const fileInputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadTab(activeTab);
  }, [activeTab]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadTab(tab) {
    setTabLoading(true);
    setTabError(null);
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
      setTabData(result);
    } catch (e) {
      setTabError(e.message || t("common.error"));
    } finally {
      setTabLoading(false);
    }
  }

  async function sendMessage(e) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setSending(true);

    try {
      const resp = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        body: JSON.stringify({
          message: text,
          user_id: user?.telegram_user_id || user?.name || "web",
          first_name: user?.name || "",
        }),
      });
      // Gate: backend says onboarding not done → redirect
      if (resp.status === 409) {
        const data = await resp.json().catch(() => ({}));
        const redirect = data?.detail?.redirect || "/onboarding";
        navigate(redirect);
        return;
      }
      const data = await resp.json();
      if (data.success) {
        setMessages((m) => [...m, { role: "assistant", text: data.reply }]);
      } else {
        setMessages((m) => [...m, { role: "assistant", text: "❌ " + (data.error || t("common.error")) }]);
      }
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: "❌ " + e.message }]);
    } finally {
      setSending(false);
      // Refresh active tab in case data changed
      loadTab(activeTab);
    }
  }

  function useExamplePrompt(prompt) {
    setInput(prompt);
  }

  async function handleUpload(files) {
    if (!files || files.length === 0) return;
    const file = files[0];
    setUploading(true);
    setMessages((m) => [...m, { role: "user", text: `📎 ${file.name}` }]);

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("filename", file.name);
      form.append("mime_type", file.type || "application/octet-stream");
      form.append("user_id", user?.name || "web");

      // Auth token goes in X-Upload-Token header — never set Content-Type
      // manually on multipart (browser sets it with the boundary).
      const headers = {};
      if (UPLOAD_TOKEN) headers["X-Upload-Token"] = UPLOAD_TOKEN;

      const resp = await fetch(`${UPLOAD_URL}/upload`, {
        method: "POST",
        headers,
        body: form,
      });
      const data = await resp.json().catch(() => ({}));
      if (resp.ok && data.status === "queued") {
        setMessages((m) => [...m, {
          role: "assistant",
          text: `📄 "${data.filename}" received — processing in the background.`,
        }]);
      } else {
        const errMsg = data.detail || data.error || `Upload failed (HTTP ${resp.status})`;
        setMessages((m) => [...m, { role: "assistant", text: `❌ ${errMsg}` }]);
      }
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: `❌ ${e.message}` }]);
    } finally {
      setUploading(false);
      loadTab(activeTab);
    }
  }

  function onDragOver(e) {
    e.preventDefault();
    setDragging(true);
  }
  function onDragLeave() {
    setDragging(false);
  }
  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    handleUpload(e.dataTransfer.files);
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
        position: "sticky", top: 0, background: "var(--bg-base)", zIndex: 10,
      }}>
        <span style={{ fontWeight: 700 }}>🧠 {t("app.name")}</span>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <LanguageSwitcher lang={lang} setLang={setLang} />
          <a href="/settings" className="btn btn-ghost btn-sm">{t("nav.settings")}</a>
          <button onClick={logout} className="btn btn-ghost btn-sm">{t("nav.logout")}</button>
        </div>
      </nav>

      <div style={{ maxWidth: "1000px", margin: "0 auto", padding: "24px", display: "grid", gridTemplateColumns: "1fr 360px", gap: "24px" }}>

        {/* Left column — Chat */}
        <div>
          <h1 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "16px" }}>
            {t("dashboard.welcome")}, {user?.name || "User"} 👋
          </h1>

          {/* Chat panel */}
          <div
            className="card"
            style={{
              padding: 0,
              display: "flex",
              flexDirection: "column",
              height: "500px",
              border: dragging ? "2px dashed var(--brand)" : undefined,
            }}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
          >
            {/* Messages */}
            <div style={{ flex: 1, overflowY: "auto", padding: "20px" }}>
              {messages.length === 0 ? (
                <div style={{ padding: "24px 20px", textAlign: "center" }}>
                  <div style={{ fontSize: "48px", marginBottom: "12px" }}>🧠</div>
                  <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "8px" }}>
                    {t("dashboard.chat_empty_title")}
                  </h2>
                  <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "20px", lineHeight: 1.5 }}>
                    {t("dashboard.chat_empty_hint")}
                  </p>

                  {/* Primary CTA — upload your first document */}
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="btn btn-brand btn-lg"
                    style={{ marginBottom: "20px", padding: "12px 24px" }}
                  >
                    {t("dashboard.empty_cta_upload")}
                  </button>

                  {/* Example prompts */}
                  <div style={{ marginTop: "12px", textAlign: "left" }}>
                    <p style={{
                      fontSize: "12px",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      color: "var(--text-tertiary)",
                      fontWeight: 600,
                      marginBottom: "8px",
                      textAlign: "center",
                    }}>
                      {t("dashboard.empty_example_title")}
                    </p>
                    {[
                      t("dashboard.empty_example_1"),
                      t("dashboard.empty_example_2"),
                      t("dashboard.empty_example_3"),
                    ].map((ex, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => useExamplePrompt(ex)}
                        className="btn btn-outline btn-sm"
                        style={{
                          display: "block",
                          width: "100%",
                          textAlign: "left",
                          padding: "10px 14px",
                          marginBottom: "6px",
                          fontSize: "13px",
                          lineHeight: 1.4,
                        }}
                      >
                        💬 {ex}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((m, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      justifyContent: m.role === "user" ? "flex-end" : "flex-start",
                      marginBottom: "12px",
                    }}
                  >
                    <div
                      style={{
                        maxWidth: "80%",
                        padding: "10px 14px",
                        borderRadius: "var(--radius-md)",
                        background: m.role === "user" ? "var(--brand)" : "var(--bg-surface)",
                        color: m.role === "user" ? "var(--text-on-brand)" : "var(--text-primary)",
                        fontSize: "14px",
                        lineHeight: 1.5,
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                      }}
                    >
                      {m.text}
                    </div>
                  </div>
                ))
              )}
              {(sending || uploading) && (
                <div style={{ textAlign: "center", padding: "8px", color: "var(--text-secondary)", fontSize: "13px" }}>
                  {uploading ? "📄 Processing..." : "💭 Thinking..."}
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input bar */}
            <form
              onSubmit={sendMessage}
              style={{
                display: "flex",
                gap: "8px",
                padding: "12px",
                borderTop: "1px solid var(--border-light)",
                background: "var(--bg-base)",
              }}
            >
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="btn btn-ghost btn-sm"
                style={{ padding: "8px 12px" }}
                title={t("dashboard.upload_hint") || "Upload document"}
              >
                📎
              </button>
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: "none" }}
                accept="image/*,.pdf"
                onChange={(e) => handleUpload(e.target.files)}
              />
              <input
                type="text"
                className="input"
                placeholder={t("dashboard.chat_placeholder") || "Ask anything..."}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={sending}
                style={{ flex: 1, fontSize: "14px" }}
              />
              <button
                type="submit"
                className="btn btn-brand btn-sm"
                disabled={!input.trim() || sending}
                style={{ padding: "8px 16px" }}
              >
                {t("common.send") || "Send"}
              </button>
            </form>
          </div>

          <p style={{ textAlign: "center", marginTop: "12px", fontSize: "12px", color: "var(--text-tertiary)" }}>
            💬 Or use Telegram: <a href="https://t.me/SaveMyBrainSC_bot" target="_blank" style={{ color: "var(--brand)" }}>@SaveMyBrainSC_bot</a>
          </p>
        </div>

        {/* Right column — Data tabs */}
        <div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "12px" }}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`btn btn-sm ${activeTab === tab.id ? "btn-primary" : "btn-outline"}`}
                style={{ padding: "6px 12px", fontSize: "12px" }}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          <div className="card" style={{ padding: "16px", maxHeight: "500px", overflowY: "auto" }}>
            {tabLoading ? (
              <p style={{ opacity: 0.5, fontSize: "13px" }}>{t("common.loading")}</p>
            ) : tabError ? (
              <p style={{ color: "var(--danger)", fontSize: "13px" }}>{tabError}</p>
            ) : (
              <TabContent tab={activeTab} data={tabData} t={t} />
            )}
          </div>
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
        <p style={{ opacity: 0.5, fontSize: "13px" }}>{t("dashboard.no_tasks")}</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {data.tasks?.map((task, i) => (
            <li key={i} style={{ padding: "6px 0", borderBottom: "1px solid var(--border-light)", fontSize: "13px" }}>
              <span className={`badge badge-${task.priority === "P1" ? "danger" : task.priority === "P2" ? "warning" : "info"}`} style={{ marginRight: "6px" }}>
                {task.priority}
              </span>
              {task.description}
            </li>
          ))}
        </ul>
      );

    case "deadlines":
      return data.count === 0 ? (
        <p style={{ opacity: 0.5, fontSize: "13px" }}>{t("dashboard.no_deadlines")}</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {data.dates?.map((d, i) => (
            <li key={i} style={{ padding: "6px 0", borderBottom: "1px solid var(--border-light)", fontSize: "13px" }}>
              <span className={`badge badge-${d.priority === "P1" ? "danger" : d.priority === "P2" ? "warning" : "info"}`} style={{ marginRight: "6px" }}>
                {d.days_until}d
              </span>
              <strong>{d.date}</strong> — {d.label}
            </li>
          ))}
        </ul>
      );

    case "finances":
      return (data.total || 0) === 0 && Object.keys(data.by_category || {}).length === 0 ? (
        <p style={{ opacity: 0.5, fontSize: "13px" }}>{t("dashboard.no_finances")}</p>
      ) : (
        <div>
          <h3 style={{ fontSize: "14px", marginBottom: "12px" }}>
            {data.period} — ${Math.abs(data.total || 0).toFixed(2)}
          </h3>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {Object.entries(data.by_category || {}).map(([cat, amount]) => (
              <li key={cat} style={{ padding: "4px 0", display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
                <span style={{ textTransform: "capitalize" }}>{cat}</span>
                <span style={{ fontWeight: 600 }}>${Math.abs(amount).toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </div>
      );

    case "documents":
      return (data.count || 0) === 0 ? (
        <p style={{ opacity: 0.5, fontSize: "13px" }}>{t("dashboard.no_documents")}</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {data.matches?.map((doc, i) => (
            <li key={i} style={{ padding: "8px 0", borderBottom: "1px solid var(--border-light)", fontSize: "13px" }}>
              <strong>{doc.title}</strong>
              <p style={{ fontSize: "12px", opacity: 0.7, marginTop: "4px" }}>{doc.excerpt}</p>
            </li>
          ))}
        </ul>
      );

    case "family":
      if (!data.primary_user && (!data.household_members || data.household_members.length === 0)) {
        return <p style={{ opacity: 0.5, fontSize: "13px" }}>{t("dashboard.no_family")}</p>;
      }
      return (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {data.primary_user?.name && (
            <li style={{ padding: "6px 0", borderBottom: "1px solid var(--border-light)", fontSize: "13px" }}>
              👤 <strong>{data.primary_user.name}</strong> <span style={{ opacity: 0.5, fontSize: "11px" }}>(you)</span>
            </li>
          )}
          {data.household_members?.map((m, i) => (
            <li key={i} style={{ padding: "6px 0", borderBottom: "1px solid var(--border-light)", fontSize: "13px" }}>
              👤 {m.name}
            </li>
          ))}
        </ul>
      );

    default:
      return null;
  }
}
