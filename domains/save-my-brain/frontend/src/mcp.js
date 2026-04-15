/**
 * Web API Client — talks to the save-my-brain web API.
 *
 * Simple REST wrapper around the extension tools (not full MCP protocol).
 * The web API runs on port 8091 and wraps the same dispatch() function
 * that MCP uses internally.
 *
 * Endpoints:
 *   GET  /api/health              — health check (public)
 *   GET  /api/context             — all context files
 *   GET  /api/context/{category}  — one context file
 *   POST /api/tool/{name}         — call a tool with JSON args
 *   GET  /api/tools               — list all tools
 */

import { getAuthHeaders } from "./auth";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8091";

async function callTool(toolName, args = {}) {
  const resp = await fetch(`${API_URL}/api/tool/${toolName}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(args),
  });

  if (!resp.ok) {
    const errText = await resp.text().catch(() => resp.statusText);
    throw new Error(`API call failed (${resp.status}): ${errText}`);
  }

  const data = await resp.json();
  if (!data.success) {
    throw new Error(data.error || "Tool call failed");
  }
  return data.result;
}

// ---------------------------------------------------------------------------
// Domain tools
// ---------------------------------------------------------------------------

export const searchDocuments = (query, docType) =>
  callTool("search_documents", { query, doc_type: docType });

export const listTasks = (status = "pending") =>
  callTool("list_tasks", { status });

export const listExpiryDates = (daysAhead = 90) =>
  callTool("list_expiry_dates", { days_ahead: daysAhead });

export const getFinancialSummary = (period = "this_month") =>
  callTool("get_financial_summary", { period });

export const listFamilyMembers = () =>
  callTool("list_family_members", {});

export const addFamilyMember = (name) =>
  callTool("add_family_member", { name });

export const removeFamilyMember = (name) =>
  callTool("remove_family_member", { name });

export const renameFamilyMember = (oldName, newName) =>
  callTool("rename_family_member", { old_name: oldName, new_name: newName });

// ---------------------------------------------------------------------------
// Context files
// ---------------------------------------------------------------------------

export async function getContext(category) {
  const url = category
    ? `${API_URL}/api/context/${category}`
    : `${API_URL}/api/context`;
  const resp = await fetch(url, { headers: getAuthHeaders() });
  if (!resp.ok) throw new Error(`Context fetch failed: ${resp.status}`);
  return resp.json();
}

// ---------------------------------------------------------------------------
// Health check (public — no auth required)
// ---------------------------------------------------------------------------

export async function checkHealth() {
  try {
    const resp = await fetch(`${API_URL}/api/health`);
    if (!resp.ok) return false;
    const data = await resp.json();
    return data.status === "ok";
  } catch {
    return false;
  }
}
