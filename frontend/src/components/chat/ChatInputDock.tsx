import { useId, useState } from 'react'

export function ChatInputDock({
  placeholder,
  onSend,
  disabled = false,
}: {
  placeholder: string
  onSend: (text: string) => void
  disabled?: boolean
}) {
  const inputId = useId()
  const [value, setValue] = useState('')

  return (
    <div className="pointer-events-none absolute bottom-8 left-1/2 w-full max-w-3xl -translate-x-1/2 px-6 z-30">
      <div className="pointer-events-auto group flex items-center gap-2 rounded-2xl border border-outline-variant/20 bg-surface-container-high/80 backdrop-blur-2xl p-2 shadow-[0_10px_50px_rgba(0,0,0,0.50)] transition-all duration-300 focus-within:border-primary/30 focus-within:shadow-[0_0_30px_rgba(59,191,250,0.10)]">
        <button
          type="button"
          className="flex-shrink-0 rounded-xl p-3 text-on-surface/60 transition-colors hover:bg-surface-container-highest hover:text-primary"
          aria-label="Add attachment"
        >
          <span className="material-symbols-outlined text-[22px]">
            add_circle
          </span>
        </button>

        <label className="sr-only" htmlFor={inputId}>
          Chat message
        </label>
        <input
          id={inputId}
          className="flex-1 bg-transparent px-2 py-3 font-body text-sm text-on-surface outline-none placeholder:text-on-surface/40"
          placeholder={placeholder}
          value={value}
          disabled={disabled}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              const text = value
              setValue('')
              onSend(text)
            }
          }}
        />

        <button
          type="button"
          className="relative flex-shrink-0 overflow-hidden rounded-xl bg-gradient-to-br from-primary to-primary-container p-3 text-surface-container-lowest shadow-[0_0_20px_rgba(59,191,250,0.20)] transition-all hover:shadow-[0_0_30px_rgba(59,191,250,0.40)]"
          aria-label="Send message"
          disabled={disabled}
          onClick={() => {
            const text = value
            setValue('')
            onSend(text)
          }}
        >
          <div className="absolute left-0 right-0 top-0 h-[2px] bg-white/20" />
          <span
            className="material-symbols-outlined text-[20px]"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            send
          </span>
        </button>
      </div>

      <div className="pointer-events-auto mt-3 text-center text-[10px] font-semibold uppercase tracking-widest text-on-surface/30">
        Kinetic Vault AI generates predictive models. Verify critical outputs.
      </div>
    </div>
  )
}

