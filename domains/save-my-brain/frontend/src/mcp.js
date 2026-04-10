/**
 * MCP Client — talks to simply-connect MCP server via JSON-RPC over HTTP.
 *
 * In dev: Vite proxies /mcp → localhost:3004
 * In prod: Configure VITE_MCP_URL or reverse proxy
 */

const MCP_URL = import.meta.env.VITE_MCP_URL || "";

async function mcpCall(toolName, args = {}) {
  const resp = await fetch(`${MCP_URL}/mcp/messages/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: { name: toolName, arguments: args },
    }),
  });

  if (!resp.ok) {
    throw new Error(`MCP call failed: ${resp.status} ${resp.statusText}`);
  }

  const data = await resp.json();

  if (data.error) {
    throw new Error(data.error.message || "MCP error");
  }

  // Parse the tool result — MCP returns { result: { content: [{ text: "..." }] } }
  const text = data.result?.content?.[0]?.text || "{}";
  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

// ---------------------------------------------------------------------------
// Domain tools (from save-my-brain extension)
// ---------------------------------------------------------------------------

export const searchDocuments = (query, docType) =>
  mcpCall("search_documents", { query, doc_type: docType });

export const listTasks = (status = "pending") =>
  mcpCall("list_tasks", { status });

export const listExpiryDates = (daysAhead = 90) =>
  mcpCall("list_expiry_dates", { days_ahead: daysAhead });

export const getFinancialSummary = (period = "this_month") =>
  mcpCall("get_financial_summary", { period });

export const listFamilyMembers = () =>
  mcpCall("list_family_members", {});

// ---------------------------------------------------------------------------
// Context tools (from simply-connect core)
// ---------------------------------------------------------------------------

export const getContext = (category) =>
  mcpCall("get_committed_context", category ? { category } : {});

export const captureToStaging = (summary, content, category) =>
  mcpCall("capture_to_staging", { summary, content, category });

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

export async function checkMcpHealth() {
  try {
    const resp = await fetch(`${MCP_URL}/mcp/messages/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/list",
        params: {},
      }),
    });
    return resp.ok;
  } catch {
    return false;
  }
}
