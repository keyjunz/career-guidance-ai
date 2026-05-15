export type SourceCardProps = {
  rank?: number
  displayTitle: string
  subtitle?: string | null
  linkHref: string
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

export function SourceCard({
  rank,
  displayTitle,
  subtitle,
  linkHref,
  isFileLink = false,
}: SourceCardProps) {
  const icon = !isFileLink && linkHref.startsWith('http') ? faviconUrl(linkHref) : ''
  const linkLabel = isFileLink ? 'Mở tệp PDF' : 'Mở liên kết'

  return (
    <a
      href={linkHref}
      target="_blank"
      rel="noreferrer"
      title={isFileLink ? linkHref : undefined}
      className="source-card u-focus flex items-start gap-2 rounded-xl bg-surface-container-high/80 px-3 py-2.5 shadow-sm transition hover:bg-surface-container-high"
    >
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
      <span className="min-w-0 flex-1">
        <span className="flex items-start gap-1">
          {typeof rank === 'number' ? (
            <span className="mr-0.5 shrink-0 text-[10px] font-bold text-primary/80">
              #{rank}
            </span>
          ) : null}
          <span className="text-[13px] font-semibold leading-snug text-on-surface/90">
            {displayTitle}
          </span>
        </span>
        {subtitle ? (
          <span className="mt-0.5 block text-[11px] text-on-surface/55">{subtitle}</span>
        ) : null}
        <span className="mt-1 block text-[12px] font-medium text-primary/90">{linkLabel}</span>
      </span>
      <span
        className="material-symbols-outlined shrink-0 text-[18px] text-on-surface/40"
        aria-hidden
      >
        open_in_new
      </span>
    </a>
  )
}
