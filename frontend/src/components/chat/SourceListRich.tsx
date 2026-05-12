import { useMemo, useState } from 'react'
import { SourceCard } from './SourceCard'
import { normalizeSourceRow } from '../../utils/sourceDisplay'

function tokenizeForHighlight(text: string): string[] {
  return text
    .toLowerCase()
    .split(/\s+/)
    .map((w) => w.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, ''))
    .filter((w) => w.length >= 3)
    .slice(0, 12)
}

export function SourceListRich({
  sources,
  initialVisible = 3,
}: {
  sources: Array<Record<string, unknown>>
  initialVisible?: number
}) {
  const [expanded, setExpanded] = useState(false)
  const normalized = useMemo(() => {
    const rows = sources
      .map((raw) => normalizeSourceRow(raw))
      .filter((row): row is NonNullable<typeof row> => row !== null)
    return rows
  }, [sources])

  const highlightPool = useMemo(() => {
    const bag = new Set<string>()
    normalized.forEach((n) => {
      tokenizeForHighlight(n.displayTitle).forEach((t) => bag.add(t))
      tokenizeForHighlight(n.snippet).forEach((t) => bag.add(t))
    })
    return Array.from(bag).slice(0, 10)
  }, [normalized])

  if (normalized.length === 0) return null

  const visible = expanded ? normalized : normalized.slice(0, initialVisible)

  return (
    <div className="rounded-xl bg-surface-container-high/90 px-3 py-2 dark:bg-surface-container-high/75">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface/45">
        Nguồn tham khảo
      </p>
      <div className="flex flex-col gap-2">
        {visible.map((item) => (
          <SourceCard
            key={`${item.linkHref}-${item.displayTitle}-${item.rank ?? 0}`}
            rank={item.rank}
            displayTitle={item.displayTitle}
            subtitle={item.subtitle}
            linkHref={item.linkHref}
            snippetText={item.snippet}
            highlightTerms={highlightPool}
            isFileLink={item.isFileLink}
          />
        ))}
      </div>
      {normalized.length > initialVisible ? (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="mt-2 text-[12px] font-medium text-primary/90 u-focus rounded-lg px-1 py-0.5"
        >
          {expanded ? 'Thu gọn' : `Xem thêm (${normalized.length - initialVisible})`}
        </button>
      ) : null}
    </div>
  )
}
