/**
 * Auth helpers — lightweight token-based auth.
 *
 * For now: simple localStorage token.
 * Future: Supabase Auth or Telegram-generated tokens.
 */

const TOKEN_KEY = "smb_token";
const USER_KEY = "smb_user";

export function isLoggedIn() {
  return !!localStorage.getItem(TOKEN_KEY);
}

export function getUser() {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function login(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  window.location.href = "/";
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
