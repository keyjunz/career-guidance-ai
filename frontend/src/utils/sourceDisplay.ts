/** Normalize RAG / web source rows for UI: friendly title, openable href, snippet. */

const SNIPPET_MAX = 360

export type NormalizedSourceRow = {
  rank?: number
  /** PDF / page title — never raw Windows path as primary label */
  displayTitle: string
  /** Short hint under title (not full D:\...) */
  subtitle: string | null
  /** href for "open" — https or file:/// */
  linkHref: string
  snippet: string
  /** true if link is file:// (may be restricted by browser) */
  isFileLink: boolean
}

function basenameFromPath(p: string): string {
  const s = p.trim().replace(/\\/g, '/')
  const parts = s.split('/').filter(Boolean)
  return parts.length ? (parts[parts.length - 1] ?? s) : s
}

export function isHttpUrl(s: string): boolean {
  return /^https?:\/\//i.test(s.trim())
}

export function looksLikeLocalFilesystemPath(s: string): boolean {
  const t = s.trim()
  if (!t) return false
  if (isHttpUrl(t)) return false
  if (/^[a-zA-Z]:[\\/]/.test(t)) return true
  if (t.startsWith('\\\\')) return true
  if (t.startsWith('/') && !t.startsWith('//')) return true
  return false
}

/** Build file:/// URL for local paths (Windows + POSIX). */
export function localPathToFileHref(absPath: string): string {
  let p = absPath.trim().replace(/\\/g, '/')
  if (/^[a-zA-Z]:\//.test(p)) {
    return `file:///${p}`
  }
  if (p.startsWith('//')) {
    return `file:${p}`
  }
  if (p.startsWith('/')) {
    return `file://${p}`
  }
  return p
}

function clipSnippet(raw: string, maxLen = SNIPPET_MAX): string {
  const t = raw.replace(/\s+/g, ' ').trim()
  if (t.length <= maxLen) return t
  return `${t.slice(0, maxLen).trim()}…`
}

export function normalizeSourceRow(raw: Record<string, unknown>): NormalizedSourceRow | null {
  const titleRaw = String(raw.title ?? '').trim()
  const sourceRaw = String(raw.source ?? '').trim()
  const urlRaw = String(raw.url ?? '').trim()
  const textRaw = String(raw.text ?? raw.snippet ?? '').trim()
  const rank = typeof raw.rank === 'number' ? raw.rank : undefined

  const httpCandidate = [urlRaw, sourceRaw].find((s) => s && isHttpUrl(s)) ?? ''
  const pathCandidate =
    [sourceRaw, urlRaw].find((s) => s && looksLikeLocalFilesystemPath(s)) ?? ''

  const looksTitle = titleRaw.length > 0 && !looksLikeLocalFilesystemPath(titleRaw)
  let displayTitle = looksTitle
    ? titleRaw
    : basenameFromPath(pathCandidate || titleRaw || sourceRaw || urlRaw)
  if (!displayTitle) return null

  let linkHref = ''
  let isFileLink = false
  if (httpCandidate) {
    linkHref = httpCandidate
  } else if (pathCandidate && looksLikeLocalFilesystemPath(pathCandidate)) {
    linkHref = localPathToFileHref(pathCandidate)
    isFileLink = true
  } else if (sourceRaw && isHttpUrl(sourceRaw)) {
    linkHref = sourceRaw
  } else if (urlRaw && !looksLikeLocalFilesystemPath(urlRaw)) {
    linkHref = urlRaw
  } else {
    linkHref = pathCandidate ? localPathToFileHref(pathCandidate) : ''
    isFileLink = Boolean(pathCandidate)
  }

  if (!linkHref) return null

  let subtitle: string | null = null
  if (isHttpUrl(linkHref)) {
    try {
      subtitle = new URL(linkHref).hostname
    } catch {
      subtitle = null
    }
  } else if (isFileLink) {
    subtitle = 'Tệp trên máy'
  }

  return {
    rank,
    displayTitle,
    subtitle,
    linkHref,
    snippet: textRaw ? clipSnippet(textRaw) : '',
    isFileLink,
  }
}
