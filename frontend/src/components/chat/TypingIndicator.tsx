export function TypingIndicator() {
  return (
    <div className="flex gap-4 max-w-3xl">
      <div className="h-10 w-10 rounded-xl bg-surface-container-highest border border-outline-variant/10 flex items-center justify-center flex-shrink-0">
        <span
          className="material-symbols-outlined text-on-surface/60 text-[20px]"
          style={{ fontVariationSettings: "'FILL' 1" }}
        >
          generating_tokens
        </span>
      </div>

      <div className="mt-2 flex h-10 w-fit items-center gap-1.5 rounded-2xl rounded-tl-sm bg-surface-container-low px-4 py-3">
        <span
          className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce"
          style={{ animationDelay: '0ms' }}
        />
        <span
          className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce"
          style={{ animationDelay: '150ms' }}
        />
        <span
          className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce"
          style={{ animationDelay: '300ms' }}
        />
      </div>
    </div>
  )
}

