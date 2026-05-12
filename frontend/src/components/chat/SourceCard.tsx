import { useMemo, useState, type ReactNode } from 'react'

export type SourceCardProps = {
  rank?: number
  displayTitle: string
  subtitle?: string | null
  linkHref: string
  snippetText: string
  highlightTerms?: string[]
  isFileLink?: boolean
}

function faviconUrl(pageUrl: string): string {
  try {
    const u = new URL(pageUrl.startsWith('http') ? pageUrl : `https://${pageUrl}`)
    return `https://www.google.com/s2/favicons?domain=${u.hostname}&sz=32`
  } catch {
    return ''
  }
}

function buildSnippet(raw: string, maxLen: number): string {
  const t = raw.replace(/\s+/g, ' ').trim()
  if (t.length <= maxLen) return t
  return `${t.slice(0, maxLen).trim()}…`
}

function highlightSnippet(text: string, terms: string[]): ReactNode {
  if (!terms.length) return text
  const lower = text.toLowerCase()
  const ranges: { start: number; end: number }[] = []
  for (const term of terms) {
    const q = term.trim().toLowerCase()
    if (q.length < 2) continue
    let from = 0
    while (from < lower.length) {
      const idx = lower.indexOf(q, from)
      if (idx < 0) break
      ranges.push({ start: idx, end: idx + q.length })
      from = idx + q.length
    }
  }
  if (!ranges.length) return text
  ranges.sort((a, b) => a.start - b.start)
  const merged: { start: number; end: number }[] = []
  for (const r of ranges) {
    const last = merged[merged.length - 1]
    if (!last || r.start > last.end) merged.push({ ...r })
    else last.end = Math.max(last.end, r.end)
  }
  const parts: ReactNode[] = []
  let cursor = 0
  merged.forEach((r, i) => {
    if (r.start > cursor) parts.push(text.slice(cursor, r.start))
    parts.push(
      <mark
        key={`h-${i}-${r.start}`}
        className="rounded-sm bg-primary/22 px-0.5 text-on-surface"
      >
        {text.slice(r.start, r.end)}
      </mark>,
    )
    cursor = r.end
  })
  if (cursor < text.length) parts.push(text.slice(cursor))
  return <>{parts}</>
}

export function SourceCard({
  rank,
  displayTitle,
  subtitle,
  linkHref,
  snippetText,
  highlightTerms = [],
  isFileLink = false,
}: SourceCardProps) {
  const [open, setOpen] = useState(false)
  const snippet = useMemo(
    () => (snippetText ? buildSnippet(snippetText, open ? 2000 : 220) : ''),
    [snippetText, open],
  )
  const icon = !isFileLink && linkHref.startsWith('http') ? faviconUrl(linkHref) : ''

  const linkLabel = isFileLink ? 'Mở tệp PDF' : 'Mở liên kết'

  return (
    <div className="source-card rounded-xl bg-surface-container-high/80 px-3 py-2.5 shadow-sm">
      <div className="flex w-full items-start gap-2">
        {icon ? (
          <img
            src={icon}
            alt=""
            className="mt-0.5 h-5 w-5 shrink-0 rounded-sm bg-surface-container p-0.5"
            loading="lazy"
          />
        ) : (
          <span
            className="material-symbols-outlined mt-0.5 shrink-0 text-[18px] text-primary/80"
            style={{ fontVariationSettings: "'FILL' 0" }}
          >
            {isFileLink ? 'description' : 'link'}
          </span>
        )}
        <div className="min-w-0 flex-1">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex w-full items-start gap-1 rounded-lg text-left u-focus"
          >
            {typeof rank === 'number' ? (
              <span className="mr-1 shrink-0 text-[10px] font-bold text-primary/80">
                #{rank}
              </span>
            ) : null}
            <span className="min-w-0 flex-1">
              <span className="text-[13px] font-semibold leading-snug text-on-surface/90">
                {displayTitle}
              </span>
              {subtitle ? (
                <span className="mt-0.5 block text-[11px] text-on-surface/45">{subtitle}</span>
              ) : null}
            </span>
            <span
              className={`material-symbols-outlined shrink-0 text-[20px] text-on-surface/40 transition ${
                open ? 'rotate-180' : ''
              }`}
            >
              expand_more
            </span>
          </button>
          {snippet ? (
            <p
              className={`mt-2 text-[12px] leading-relaxed text-on-surface/72 ${
                open ? '' : 'line-clamp-3'
              }`}
            >
              {highlightSnippet(snippet, highlightTerms)}
            </p>
          ) : null}
          <a
            href={linkHref}
            target="_blank"
            rel="noreferrer"
            title={isFileLink ? linkHref : undefined}
            className="mt-2 inline-flex text-[12px] font-medium text-primary/90 underline decoration-primary/30 underline-offset-2"
          >
            {linkLabel}
          </a>
        </div>
      </div>
    </div>
  )
}
