/**
 * Where the backend lives.
 *
 * The Vite dev server proxies /api, /.well-known and /ws to FastAPI, so by default
 * everything stays same-origin. VITE_API_URL / VITE_WS_URL only need to be set if
 * the backend runs on a different address.
 */
export const API_ORIGIN = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '');

export const API_BASE = `${API_ORIGIN}/api/v1`;

/** Turns a backend path like "/.well-known/wipe-keys" into a full URL. */
export const apiUrl = (path: string) => `${API_ORIGIN}${path}`;

export function wsUrl(): string {
  const explicit = (import.meta.env.VITE_WS_URL || '').trim();
  if (explicit) return explicit;
  if (API_ORIGIN) return `${API_ORIGIN.replace(/^http/, 'ws')}/ws`;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws`;
}
