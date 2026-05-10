import { API_BASE_URL } from '../services/apiClient'

function apiOrigin(): string {
  try {
    return new URL(API_BASE_URL).origin
  } catch {
    return API_BASE_URL.replace(/\/$/, '')
  }
}

/**
 * Resolve image URLs from the chat API for display in the browser.
 * Relative `/images/...` and mismatched localhost ports are normalized to `API_BASE_URL`.
 */
export function resolveApiMediaUrl(url: string): string {
  const raw = url.trim()
  if (!raw) return raw

  const origin = apiOrigin()

  if (/^https?:\/\//i.test(raw)) {
    try {
      const u = new URL(raw)
      if (u.hostname === 'localhost' || u.hostname === '127.0.0.1') {
        return `${origin}${u.pathname}${u.search}${u.hash}`
      }
    } catch {
      return raw
    }
    return raw
  }

  if (raw.startsWith('/')) {
    return `${origin}${raw}`
  }

  return `${origin}/${raw.replace(/^\//, '')}`
}
