import { useEffect, useLayoutEffect, useRef } from 'react'
import { MessageBubble } from './MessageBubble'
import type { ChatMessage } from '../../types/chat'

const STARTER_CHIPS: Array<{ icon: string; label: string; prompt: string }> = [
  {
    icon: 'work',
    label: 'Gợi ý hướng nghiệp',
    prompt:
      'Dựa trên xu hướng thị trường hiện tại, gợi ý giúp tôi vài hướng nghiệp phù hợp để bắt đầu.',
  },
  {
    icon: 'school',
    label: 'Kỹ năng nên học',
    prompt: 'Tôi nên ưu tiên học thêm những kỹ năng nào để tăng cơ hội việc làm?',
  },
  {
    icon: 'compare_arrows',
    label: 'So sánh ngành học',
    prompt:
      'So sánh ngắn gọn các nhóm ngành công nghệ (ví dụ phần mềm, dữ liệu, an ninh) về cơ hội và yêu cầu.',
  },
  {
    icon: 'tips_and_updates',
    label: 'Chuẩn bị phỏng vấn',
    prompt: 'Gợi ý cách chuẩn bị phỏng vấn và vài câu hỏi thường gặp cho vị trí entry-level.',
  },
]

export function ChatThread({
  messages,
  dayChip,
  isTyping,
  errorMessage,
  userFirstName,
  onStarterPrompt,
}: {
  messages: ChatMessage[]
  dayChip: string
  isTyping: boolean
  errorMessage?: string
  /** First name or short display name for empty-state greeting */
  userFirstName?: string
  /** Fills the composer flow with a preset prompt (same as typing send) */
  onStarterPrompt?: (text: string) => void
}) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const latestTurnUserId = useRef('')

  let latestUserMessageId = ''
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'user') {
      latestUserMessageId = messages[i].id
      break
    }
  }

  useLayoutEffect(() => {
    const container = containerRef.current
    if (!container) return

    if (latestUserMessageId && latestTurnUserId.current !== latestUserMessageId) {
      latestTurnUserId.current = latestUserMessageId
      const latestUserElement = container.querySelector<HTMLElement>(
        `[data-message-id="${latestUserMessageId}"]`,
      )
      if (latestUserElement) {
        const targetTop = latestUserElement.offsetTop - 12
        container.scrollTo({ top: Math.max(targetTop, 0), behavior: 'smooth' })
      }
    }
  }, [latestUserMessageId, messages.length])

  useEffect(() => {
    const container = containerRef.current
    if (!container || !isTyping) return

    const distanceToBottom =
      container.scrollHeight - (container.scrollTop + container.clientHeight)
    if (distanceToBottom < 120) {
      container.scrollTo({ top: container.scrollHeight, behavior: 'auto' })
    }
  }, [isTyping, messages])

  const isEmpty = messages.length === 0
  const greetName = userFirstName?.trim() || 'bạn'
  const startersDisabled = isTyping || !onStarterPrompt

  const lastMessage = messages.length > 0 ? messages[messages.length - 1] : undefined
  const streamingMessageId =
    isTyping && lastMessage?.role === 'assistant' ? lastMessage.id : null

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 pb-44 sm:px-6"
    >
      <div className="mx-auto flex w-full max-w-[46rem] flex-col gap-3">
        {errorMessage ? (
          <div className="u-alert u-alert-error px-4 py-3 text-sm">
            {errorMessage}
          </div>
        ) : null}

        {isEmpty && !errorMessage ? (
          <div className="flex min-h-[calc(100dvh-12.5rem)] flex-col items-center justify-center px-3 py-8 text-center sm:min-h-[calc(100dvh-11.5rem)] sm:px-6">
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full border border-white/70 bg-gradient-to-br from-primary-dim/70 to-secondary/16 shadow-[0_16px_42px_rgb(42_45_43_/0.12)]">
              <span
                className="material-symbols-outlined text-[32px] text-primary"
                style={{ fontVariationSettings: "'FILL' 1, 'wght' 400" }}
              >
                auto_awesome
              </span>
            </div>
            <h2 className="font-headline max-w-lg text-[1.35rem] font-semibold leading-snug tracking-tight text-on-surface sm:text-2xl sm:leading-tight">
              Xin chào {greetName}! Chúng ta bắt đầu từ đâu nhỉ?
            </h2>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-on-surface/48">
              Hỏi về hướng nghiệp, kỹ năng hoặc lộ trình học. Chọn{' '}
              <span className="font-medium text-on-surface/62">Auto</span>,{' '}
              <span className="font-medium text-on-surface/62">RAG</span> hoặc{' '}
              <span className="font-medium text-on-surface/62">Web</span> ở ô nhập
              để đổi cách trả lời.
            </p>
            {onStarterPrompt ? (
              <div className="mt-8 flex w-full max-w-xl flex-wrap justify-center gap-2 sm:gap-2.5">
                {STARTER_CHIPS.map((chip) => (
                  <button
                    key={chip.label}
                    type="button"
                    disabled={startersDisabled}
                    onClick={() => onStarterPrompt(chip.prompt)}
                    className="u-focus inline-flex items-center gap-2 rounded-full border border-white/60 bg-surface-bright/88 px-3.5 py-2 text-left text-[13px] font-medium text-on-surface/88 shadow-[0_8px_22px_rgb(42_45_43_/0.08),inset_0_1px_0_rgb(255_255_255_/0.72)] transition hover:bg-surface-container-lowest hover:text-on-surface disabled:cursor-not-allowed disabled:opacity-45 sm:px-4 sm:py-2.5 dark:border-transparent dark:bg-surface-container-high dark:shadow-[0_4px_20px_rgb(0_0_0_/0.35)]"
                  >
                    <span className="material-symbols-outlined text-[18px] text-primary/90">
                      {chip.icon}
                    </span>
                    <span>{chip.label}</span>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {!isEmpty && (
          <div className="mb-2 flex justify-center pt-2">
            <span className="rounded-full bg-surface-container-high/90 px-3 py-1 text-[10px] font-medium uppercase tracking-wider text-on-surface/42">
              {dayChip}
            </span>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} data-message-id={m.id}>
            <MessageBubble message={m} isStreaming={streamingMessageId === m.id} />
          </div>
        ))}

        {isTyping && messages[messages.length - 1]?.role !== 'assistant' && (
          <div className="flex items-center gap-1.5 py-2 pl-1">
            {[0, 160, 320].map((delay) => (
              <span
                key={delay}
                className="h-2 w-2 rounded-full bg-on-surface/25 animate-bounce"
                style={{ animationDelay: `${delay}ms`, animationDuration: '1s' }}
              />
            ))}
          </div>
        )}
        <div className="h-1" />
      </div>
    </div>
  )
}
