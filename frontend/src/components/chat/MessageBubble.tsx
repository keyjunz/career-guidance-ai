import { useState, type ReactNode } from 'react'
import type { ChatMessage } from '../../types/chat'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import { resolveApiMediaUrl } from '../../utils/mediaUrl'
import { normalizeAssistantMarkdown } from '../../utils/normalizeAssistantMarkdown'
import { SectionedAnswer, type AnswerSection } from './SectionedAnswer'
import { SourceListRich } from './SourceListRich'
import { ImageLightbox } from './ImageLightbox'

function AgentStatusOrb({ className = '' }: { className?: string }) {
  return (
    <div className={`agent-status-wrap mt-0.5 shrink-0 self-start ${className}`.trim()} aria-hidden>
      <div className="agent-status-glow" />
      <div className="agent-status-orbit agent-status-orbit-main" />
      <div className="agent-status-orbit agent-status-orbit-trail" />
      <div className="agent-status-icon">
        <span
          className="material-symbols-outlined text-[19px]"
          style={{ fontVariationSettings: "'FILL' 1, 'wght' 400" }}
        >
          auto_awesome
        </span>
      </div>
    </div>
  )
}

function BotResponseIcon() {
  return (
    <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/14 text-primary">
      <span
        className="material-symbols-outlined text-[17px]"
        style={{ fontVariationSettings: "'FILL' 1" }}
      >
        auto_awesome
      </span>
    </div>
  )
}

function StreamReplyShell({
  isStreaming,
  children,
}: {
  isStreaming: boolean
  children: ReactNode
}) {
  if (!isStreaming) {
    return <>{children}</>
  }
  return (
    <div className="stream-reply-outer" aria-busy="true">
      <div className="stream-reply-inner px-3 py-3 sm:px-4 sm:py-3.5">{children}</div>
    </div>
  )
}

function CacheBadges({ message }: { message: ChatMessage }) {
  const cached = Boolean(message.meta?.cached)
  const retrievalHit = Boolean(message.meta?.retrieval_cache_hit)
  if (!cached && !retrievalHit) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {cached ? (
        <span className="inline-flex items-center rounded-full bg-primary/14 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary/95">
          Trả lời từ cache
        </span>
      ) : null}
      {retrievalHit ? (
        <span className="inline-flex items-center rounded-full bg-surface-container-high px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-on-surface/60">
          Tìm kiếm tái dùng
        </span>
      ) : null}
    </div>
  )
}

function BotImageTile({
  imageUrl,
  onOpen,
}: {
  imageUrl: string
  onOpen: (resolvedSrc: string) => void
}) {
  const resolved = resolveApiMediaUrl(imageUrl)
  const [broken, setBroken] = useState(false)

  if (broken) {
    return (
      <a
        href={resolved}
        target="_blank"
        rel="noreferrer"
        className="flex min-h-[100px] items-center justify-center rounded-xl bg-surface-container-high px-4 py-5 text-center text-xs font-medium text-primary underline underline-offset-2"
      >
        Image unavailable — open link
      </a>
    )
  }

  return (
    <div className="group relative overflow-hidden rounded-xl bg-surface-container-high">
      <button
        type="button"
        className="u-focus block w-full text-left"
        onClick={() => onOpen(resolved)}
        aria-haspopup="dialog"
        aria-label="Phóng to ảnh"
      >
        <img
          src={resolved}
          alt=""
          className="max-h-64 w-full cursor-zoom-in object-cover transition duration-300 group-hover:opacity-95"
          loading="lazy"
          onError={() => setBroken(true)}
        />
      </button>
      <a
        href={resolved}
        target="_blank"
        rel="noreferrer"
        className="u-focus absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center rounded-full bg-black/45 text-white shadow-sm backdrop-blur-sm transition hover:bg-black/60"
        aria-label="Mở trong tab mới"
        onClick={(e) => e.stopPropagation()}
      >
        <span
          className="material-symbols-outlined text-[18px]"
          style={{ fontVariationSettings: "'FILL' 0" }}
        >
          open_in_new
        </span>
      </a>
    </div>
  )
}

function parseAnswerSections(meta: ChatMessage['meta']): AnswerSection[] | null {
  const raw = meta?.answer_sections
  if (!Array.isArray(raw) || raw.length === 0) return null
  const out: AnswerSection[] = []
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue
    const rec = item as Record<string, unknown>
    const intent_title = String(rec.intent_title ?? '').trim()
    const query = String(rec.query ?? '').trim()
    const answer = String(rec.answer ?? '').trim()
    if (!intent_title || !answer) continue
    const sources = Array.isArray(rec.sources) ? (rec.sources as Array<Record<string, unknown>>) : []
    out.push({ intent_title, query, answer, sources })
  }
  return out.length ? out : null
}

export function MessageBubble({
  message,
  isStreaming = false,
}: {
  message: ChatMessage
  isStreaming?: boolean
}) {
  const [lightbox, setLightbox] = useState<{ src: string; alt?: string } | null>(null)
  const openImage = (rawSrc: string, alt?: string) => {
    setLightbox({ src: resolveApiMediaUrl(rawSrc), alt })
  }

  const isUser = message.role === 'user'
  const hasImages = !isUser && (message.imageUrls?.length ?? 0) > 0
  const isEmpty = !isUser && message.text === '' && !hasImages
  const isStoppedAssistant = Boolean(message.meta?.stopped)
  const isStatusStream =
    !isUser &&
    !isEmpty &&
    !isStoppedAssistant &&
    message.text.startsWith('Processing:')
  const statusLabel = isStatusStream
    ? message.text.replace('Processing:', '').trim()
    : ''
  const sources = message.meta?.sources ?? []
  const markdownText = normalizeAssistantMarkdown(message.text)
  const answerSections = !isUser ? parseAnswerSections(message.meta) : null

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[min(88%,38rem)] rounded-[1.35rem] rounded-br-md bg-surface-container-high px-4 py-2.5 text-[15px] leading-relaxed text-on-surface shadow-md dark:shadow-[0_4px_24px_rgb(0_0_0_/0.35)]">
          {message.text}
        </div>
      </div>
    )
  }

  if (isEmpty) {
    return (
      <div
        className="flex items-start gap-3 py-0.5"
        aria-busy="true"
        aria-live="polite"
        aria-label="Trợ lý đang xử lý"
      >
        <AgentStatusOrb />
      </div>
    )
  }

  if (isStatusStream) {
    return (
      <div
        className="flex min-w-0 items-center gap-3 py-0.5"
        aria-busy="true"
        aria-live="polite"
        aria-label={statusLabel}
      >
        <AgentStatusOrb />
        <span className="min-w-0 flex-1 text-[13px] font-medium leading-snug tracking-tight text-on-surface/82">
          {statusLabel}
        </span>
      </div>
    )
  }

  return (
    <>
      <StreamReplyShell isStreaming={isStreaming}>
        <div className="flex items-start gap-3">
          {isStreaming ? <AgentStatusOrb /> : <BotResponseIcon />}
          <div className="min-w-0 flex max-w-[min(92%,44rem)] flex-col gap-2.5">
          <CacheBadges message={message} />
          {answerSections && answerSections.length > 0 ? (
            <SectionedAnswer sections={answerSections} onImageClick={openImage} />
          ) : !!message.text ? (
            <div className="text-[15px] leading-[1.75] text-on-surface/88">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeSanitize]}
                components={{
                  p: ({ children }) => (
                    <p className="mb-3 last:mb-0">{children}</p>
                  ),
                  ul: ({ children }) => (
                    <ul className="mb-3 list-disc space-y-1.5 pl-5 last:mb-0 marker:text-primary/70">
                      {children}
                    </ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="mb-3 list-decimal space-y-1.5 pl-5 last:mb-0 marker:font-medium marker:text-on-surface/55">
                      {children}
                    </ol>
                  ),
                  li: ({ children }) => (
                    <li className="leading-relaxed [&>p]:mb-1 [&>p:last-child]:mb-0">
                      {children}
                    </li>
                  ),
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noreferrer"
                      className="font-medium text-primary underline decoration-primary/30 underline-offset-2"
                    >
                      {children}
                    </a>
                  ),
                  code: ({ children }) => (
                    <code className="rounded-md bg-surface-container-high px-1.5 py-0.5 text-[13px] text-on-surface/90">
                      {children}
                    </code>
                  ),
                  pre: ({ children }) => (
                    <pre className="mb-3 overflow-x-auto rounded-xl bg-surface-container-high p-3 text-[13px] last:mb-0 dark:bg-surface-container">
                      {children}
                    </pre>
                  ),
                  img: ({ src, alt }) => {
                    const raw = src ?? ''
                    if (!raw.trim()) return null
                    const resolved = resolveApiMediaUrl(raw)
                    return (
                      <button
                        type="button"
                        className="u-focus group relative my-3 block w-full max-w-full overflow-hidden rounded-xl bg-surface-container-high p-0 text-left shadow-sm ring-1 ring-on-surface/6 transition hover:ring-primary/30"
                        onClick={() => openImage(resolved, alt ?? undefined)}
                        aria-haspopup="dialog"
                        aria-label="Phóng to ảnh"
                      >
                        <img
                          src={resolved}
                          alt={alt ?? ''}
                          className="max-h-64 w-full cursor-zoom-in object-cover transition group-hover:opacity-95"
                          loading="lazy"
                        />
                      </button>
                    )
                  },
                }}
              >
                {markdownText}
              </ReactMarkdown>
            </div>
          ) : null}
          {hasImages && (
            <div className="grid gap-2 sm:grid-cols-2">
              {message.imageUrls?.map((imageUrl) => (
                <BotImageTile key={imageUrl} imageUrl={imageUrl} onOpen={openImage} />
              ))}
            </div>
          )}
          {sources.length > 0 && !(answerSections && answerSections.length) ? (
            <SourceListRich sources={sources} initialVisible={3} />
          ) : null}
        </div>
      </div>
      </StreamReplyShell>
      <ImageLightbox
        open={lightbox !== null}
        src={lightbox?.src ?? ''}
        alt={lightbox?.alt}
        onClose={() => setLightbox(null)}
      />
    </>
  )
}
