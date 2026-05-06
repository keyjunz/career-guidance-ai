import type { ChatMessage } from '../../types/chat'

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

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  const hasImages = !isUser && (message.imageUrls?.length ?? 0) > 0
  const isEmpty = !isUser && message.text === '' && !hasImages
  const isStatusStream =
    !isUser && !isEmpty && message.text.startsWith('Dang xu ly:')
  const statusLabel = isStatusStream
    ? message.text.replace('Dang xu ly:', '').trim()
    : ''

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
          <div className="text-sm leading-[1.75] text-on-surface whitespace-pre-wrap">
            {message.text}
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
      </div>
    </div>
  )
}
