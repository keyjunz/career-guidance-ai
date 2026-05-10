import type { ChatMessage } from '../../types/chat'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'

function BotLoadingDots() {
  return (
    <div className="flex items-center gap-[5px] py-1">
      <span
        className="h-[7px] w-[7px] rounded-full bg-primary/70 animate-bounce"
        style={{ animationDelay: '0ms', animationDuration: '900ms' }}
      />
      <span
        className="h-[7px] w-[7px] rounded-full bg-primary/70 animate-bounce"
        style={{ animationDelay: '180ms', animationDuration: '900ms' }}
      />
      <span
        className="h-[7px] w-[7px] rounded-full bg-primary/70 animate-bounce"
        style={{ animationDelay: '360ms', animationDuration: '900ms' }}
      />
    </div>
  )
}

function BotResponseIcon() {
  return (
    <div className="mt-1 flex h-6 w-6 items-center justify-center rounded-full border border-outline-variant/30 bg-surface-container-highest/60 text-primary">
      <span
        className="material-symbols-outlined text-[15px]"
        style={{ fontVariationSettings: "'FILL' 1" }}
      >
        auto_awesome
      </span>
    </div>
  )
}

function SourceList({ sources }: { sources: Array<Record<string, unknown>> }) {
  const normalized = sources
    .map((source) => {
      const title = String(source.title ?? '').trim()
      const url = String(source.url ?? source.source ?? '').trim()
      if (!url) return null
      return { title: title || url, url }
    })
    .filter((item): item is { title: string; url: string } => item !== null)

  if (normalized.length === 0) return null

  return (
    <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low px-3 py-2.5">
      <p className="mb-2 text-xs font-semibold tracking-wide text-on-surface/70 uppercase">
        Sources
      </p>
      <ul className="space-y-1 text-xs">
        {normalized.slice(0, 6).map((item) => (
          <li key={`${item.url}-${item.title}`}>
            <a
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="text-primary underline underline-offset-2 break-all"
            >
              {item.title}
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  const hasImages = !isUser && (message.imageUrls?.length ?? 0) > 0
  const isEmpty = !isUser && message.text === '' && !hasImages
  const isStatusStream =
    !isUser && !isEmpty && message.text.startsWith('Processing:')
  const statusLabel = isStatusStream
    ? message.text.replace('Processing:', '').trim()
    : ''
  const sources = message.meta?.sources ?? []

  // ── User message ──────────────────────────────────────────────────
  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[72%] rounded-3xl rounded-tr-md border border-outline-variant/35 bg-surface-container-high px-5 py-3.5 text-sm leading-relaxed shadow-sm">
          {message.text}
        </div>
      </div>
    )
  }

  // ── Bot: loading (empty text, waiting for first token/status) ──────
  if (isEmpty) {
    return (
      <div className="flex items-start gap-2.5">
        <BotResponseIcon />
        <BotLoadingDots />
      </div>
    )
  }

  // ── Bot: status stream ("Dang xu ly: …") ──────────────────────────
  if (isStatusStream) {
    return (
      <div className="flex items-center gap-2.5 text-sm text-on-surface/55">
        <BotResponseIcon />
        <BotLoadingDots />
        <span className="font-medium">{statusLabel}</span>
      </div>
    )
  }

  // ── Bot: real content ─────────────────────────────────────────────
  return (
    <div className="flex items-start gap-2.5">
      <BotResponseIcon />
      <div className="flex max-w-4xl flex-col gap-3">
        {!!message.text && (
          <div className="text-sm leading-[1.75] text-on-surface">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeSanitize]}
              components={{
                p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                ul: ({ children }) => (
                  <ul className="mb-3 list-disc pl-5 last:mb-0">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="mb-3 list-decimal pl-5 last:mb-0">{children}</ol>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary underline underline-offset-2"
                  >
                    {children}
                  </a>
                ),
                code: ({ children }) => (
                  <code className="rounded bg-surface-container-high px-1.5 py-0.5 text-[13px]">
                    {children}
                  </code>
                ),
                pre: ({ children }) => (
                  <pre className="mb-3 overflow-x-auto rounded-xl border border-outline-variant/20 bg-surface-container-high p-3 last:mb-0">
                    {children}
                  </pre>
                ),
              }}
            >
              {message.text}
            </ReactMarkdown>
          </div>
        )}
        {hasImages && (
          <div className="grid gap-2 sm:grid-cols-2">
            {message.imageUrls?.map((imageUrl) => (
              <a
                key={imageUrl}
                href={imageUrl}
                target="_blank"
                rel="noreferrer"
                className="group block overflow-hidden rounded-xl border border-outline-variant/25 bg-surface-container-low"
              >
                <img
                  src={imageUrl}
                  alt="Bot response visual"
                  className="h-full max-h-72 w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                  loading="lazy"
                />
              </a>
            ))}
          </div>
        )}
        {sources.length > 0 && <SourceList sources={sources} />}
      </div>
    </div>
  )
}
