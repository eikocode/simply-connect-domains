/**
 * Auth helpers — JWT-based Telegram-pairing auth.
 *
 * Token is a signed JWT issued by the backend after Telegram pairing.
 * Stored in localStorage. Sent as Authorization: Bearer <token> on every API call.
 */

const TOKEN_KEY = "smb_token";
const USER_KEY  = "smb_user";

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

/** Returns headers object with Authorization bearer token, or empty object if not logged in. */
export function getAuthHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Returns the telegram_user_id from the stored user object, or null. */
export function getTelegramUserId() {
  const user = getUser();
  return user?.telegram_user_id ?? null;
}
