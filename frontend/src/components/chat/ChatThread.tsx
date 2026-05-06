import { useEffect, useLayoutEffect, useRef } from 'react'
import { MessageBubble } from './MessageBubble'
import type { ChatMessage } from '../../types/chat'

export function ChatThread({
  messages,
  dayChip,
  isTyping,
  errorMessage,
}: {
  messages: ChatMessage[]
  dayChip: string
  isTyping: boolean
  errorMessage?: string
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

    // New user turn: push previous turns up and show latest user turn first.
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

    // While bot streams, keep following new content if user is near the bottom.
    const distanceToBottom =
      container.scrollHeight - (container.scrollTop + container.clientHeight)
    if (distanceToBottom < 120) {
      container.scrollTo({ top: container.scrollHeight, behavior: 'auto' })
    }
  }, [isTyping, messages])

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-6 pb-40"
    >
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
        {errorMessage ? (
          <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {errorMessage}
          </div>
        ) : null}

        {messages.length > 0 && (
          <div className="mb-4 flex justify-center">
            <span className="bg-surface-container-low px-4 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-widest text-on-surface/60">
              {dayChip}
            </span>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} data-message-id={m.id}>
            <MessageBubble message={m} />
          </div>
        ))}

        {/* Show fallback dots only during sync API call (no assistant bubble in list yet) */}
        {isTyping && messages[messages.length - 1]?.role !== 'assistant' && (
          <div className="flex items-center gap-[5px] py-1">
            {[0, 180, 360].map((delay) => (
              <span
                key={delay}
                className="h-[7px] w-[7px] rounded-full bg-primary/70 animate-bounce"
                style={{ animationDelay: `${delay}ms`, animationDuration: '900ms' }}
              />
            ))}
          </div>
        )}
        <div className="h-1" />
      </div>
    </div>
  )
}
