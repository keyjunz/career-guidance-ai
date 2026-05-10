import { useState } from 'react'
import type { ChatMessage } from '../../types/chat'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import { resolveApiMediaUrl } from '../../utils/mediaUrl'
import { normalizeAssistantMarkdown } from '../../utils/normalizeAssistantMarkdown'

function BotLoadingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 160, 320].map((delay) => (
        <span
          key={delay}
          className="h-2 w-2 rounded-full bg-on-surface/25 animate-bounce"
          style={{ animationDelay: `${delay}ms`, animationDuration: '1s' }}
        />
      ))}
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
    <div className="rounded-xl bg-surface-container-high/90 px-3 py-2 dark:bg-surface-container-high/75">
      <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-on-surface/45">
        Sources
      </p>
      <ul className="space-y-1 text-xs">
        {normalized.slice(0, 6).map((item) => (
          <li key={`${item.url}-${item.title}`}>
            <a
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="break-all text-primary/90 underline decoration-primary/30 underline-offset-2 transition hover:decoration-primary"
            >
              {item.title}
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}

function BotImageTile({ imageUrl }: { imageUrl: string }) {
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
    <a
      href={resolved}
      target="_blank"
      rel="noreferrer"
      className="group block overflow-hidden rounded-xl bg-surface-container-high"
    >
      <img
        src={resolved}
        alt=""
        className="max-h-64 w-full object-cover transition duration-300 group-hover:opacity-95"
        loading="lazy"
        onError={() => setBroken(true)}
      />
    </a>
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
  const markdownText = normalizeAssistantMarkdown(message.text)

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
      <div className="flex items-start gap-3">
        <BotResponseIcon />
        <BotLoadingDots />
      </div>
    )
  }

  if (isStatusStream) {
    return (
      <div className="flex items-center gap-3 text-sm text-on-surface/50">
        <BotResponseIcon />
        <BotLoadingDots />
        <span className="text-xs font-medium">{statusLabel}</span>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3">
      <BotResponseIcon />
      <div className="min-w-0 flex max-w-[min(92%,44rem)] flex-col gap-2.5">
        {!!message.text && (
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
              }}
            >
              {markdownText}
            </ReactMarkdown>
          </div>
        )}
        {hasImages && (
          <div className="grid gap-2 sm:grid-cols-2">
            {message.imageUrls?.map((imageUrl) => (
              <BotImageTile key={imageUrl} imageUrl={imageUrl} />
            ))}
          </div>
        )}
        {sources.length > 0 && <SourceList sources={sources} />}
      </div>
    </div>
  )
}
