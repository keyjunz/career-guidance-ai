import { useMemo, useState } from 'react'
import { SourceCard } from './SourceCard'
import { normalizeSourceRow } from '../../utils/sourceDisplay'

export function SourceListRich({
  sources,
  initialVisible = 3,
}: {
  sources: Array<Record<string, unknown>>
  initialVisible?: number
}) {
  const [expanded, setExpanded] = useState(false)
  const normalized = useMemo(() => {
    return sources
      .map((raw) => normalizeSourceRow(raw))
      .filter((row): row is NonNullable<typeof row> => row !== null)
  }, [sources])

  if (normalized.length === 0) return null

  const visible = expanded ? normalized : normalized.slice(0, initialVisible)

  return (
    <div className="rounded-xl bg-surface-container-high/90 px-3 py-2 dark:bg-surface-container-high/75">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface/55">
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
            isFileLink={item.isFileLink}
          />
        ))}
      </div>
      {normalized.length > initialVisible ? (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="mt-2 rounded-lg px-1 py-0.5 text-[12px] font-medium text-primary/90 u-focus"
        >
          {expanded ? 'Thu gọn' : `Xem thêm (${normalized.length - initialVisible})`}
        </button>
      ) : null}
    </div>
  )
}
