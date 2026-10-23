// localStorage wrapper: storage can be missing or throw (private mode, blocked site data).
const P = 'agri.';
export function load(key, fallback = null) {
  try {
    const v = localStorage.getItem(P + key);
    return v === null ? fallback : JSON.parse(v);
  } catch { return fallback; }
}
export function save(key, value) {
  try { localStorage.setItem(P + key, JSON.stringify(value)); return true; } catch { return false; }
}
export function clearAll() {
  try {
    Object.keys(localStorage).filter((k) => k.startsWith(P)).forEach((k) => localStorage.removeItem(k));
  } catch { /* ignore */ }
}
