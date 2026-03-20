import axios from 'axios'

/**
 * Backend base URL (no trailing slash).
 * Empty string = same origin — use Vite `server.proxy` in dev (`/api` → Django).
 * Production: set `VITE_API_BASE_URL=https://your-api.example.com`
 */
export function getApiBaseUrl() {
  const raw = import.meta.env.VITE_API_BASE_URL ?? ''
  return String(raw).trim().replace(/\/$/, '')
}

/** Shared axios instance for JSON APIs. */
export const api = axios.create({
  baseURL: getApiBaseUrl() || '',
  headers: { 'Content-Type': 'application/json' },
  timeout: 300_000,
})

/**
 * Path for fetch() (streaming, etc.). Relative when base is empty.
 * @param {string} path e.g. `/api/analyze/`
 */
export function buildApiUrl(path) {
  const base = getApiBaseUrl()
  const p = path.startsWith('/') ? path : `/${path}`
  if (!base) return p
  return `${base}${p}`
}
