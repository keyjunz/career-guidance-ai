import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'
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
  return (
    <div className="flex-1 overflow-y-auto px-10 pb-40 flex flex-col gap-10">
      {errorMessage ? (
        <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {errorMessage}
        </div>
      ) : null}

      <div className="flex justify-center mb-4">
        <span className="bg-surface-container-low px-4 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-widest text-on-surface/60">
          {dayChip}
        </span>
      </div>

      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}

      {isTyping && <TypingIndicator />}
    </div>
  )
}

