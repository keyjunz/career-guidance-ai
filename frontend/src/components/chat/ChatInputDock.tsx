import { useEffect, useId, useRef, useState } from 'react'

import type { ChatMode } from '../../types/api'

const CHAT_MODE_OPTIONS: Array<{ value: ChatMode; label: string; icon: string }> = [
  { value: 'auto', label: 'Auto', icon: 'auto_awesome' },
  { value: 'rag', label: 'RAG', icon: 'database' },
  { value: 'web', label: 'Web', icon: 'language' },
]

export function ChatInputDock({
  placeholder,
  onSend,
  disabled = false,
  chatMode = 'auto',
  onChatModeChange,
}: {
  placeholder: string
  onSend: (text: string) => void
  disabled?: boolean
  chatMode?: ChatMode
  onChatModeChange?: (mode: ChatMode) => void
}) {
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement | null>(null)
  const modeMenuRef = useRef<HTMLDivElement | null>(null)
  const [value, setValue] = useState('')
  const [isModeMenuOpen, setIsModeMenuOpen] = useState(false)

  const selectedMode =
    CHAT_MODE_OPTIONS.find((option) => option.value === chatMode) ??
    CHAT_MODE_OPTIONS[0]

  useEffect(() => {
    if (!disabled) {
      inputRef.current?.focus()
    }
  }, [disabled])

  useEffect(() => {
    if (!isModeMenuOpen) return

    const handleOutsideClick = (event: MouseEvent) => {
      const target = event.target as Node
      if (modeMenuRef.current && !modeMenuRef.current.contains(target)) {
        setIsModeMenuOpen(false)
      }
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsModeMenuOpen(false)
      }
    }

    window.addEventListener('mousedown', handleOutsideClick)
    window.addEventListener('keydown', handleEscape)
    return () => {
      window.removeEventListener('mousedown', handleOutsideClick)
      window.removeEventListener('keydown', handleEscape)
    }
  }, [isModeMenuOpen])

  const submitMessage = () => {
    const text = value.trim()
    if (!text || disabled) return
    setValue('')
    onSend(text)
  }

  return (
    <div className="absolute bottom-8 left-1/2 w-full max-w-3xl -translate-x-1/2 px-6 z-30">
      <div className="group flex items-center gap-2 rounded-2xl border border-outline-variant/20 bg-surface-container-high/80 backdrop-blur-2xl p-2 shadow-[0_10px_50px_rgba(0,0,0,0.50)] transition-all duration-300 focus-within:border-primary/30 focus-within:shadow-[0_0_30px_rgba(59,191,250,0.10)]">
        {onChatModeChange && (
          <div className="relative flex-shrink-0" ref={modeMenuRef}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => setIsModeMenuOpen((prev) => !prev)}
              className="flex items-center gap-2 rounded-xl px-3 py-2 text-on-surface/75 transition-colors hover:bg-surface-container-highest hover:text-on-surface disabled:opacity-50"
              aria-label="Select chat mode"
            >
              <span className="material-symbols-outlined text-[18px]">
                {selectedMode.icon}
              </span>
              <span className="text-sm font-semibold">{selectedMode.label}</span>
              <span className="material-symbols-outlined text-[16px]">
                {isModeMenuOpen ? 'expand_less' : 'expand_more'}
              </span>
            </button>

            {isModeMenuOpen && (
              <div className="absolute bottom-[calc(100%+8px)] left-0 min-w-[160px] overflow-hidden rounded-xl border border-outline-variant/20 bg-surface-container-high shadow-[0_12px_40px_rgba(0,0,0,0.40)]">
                {CHAT_MODE_OPTIONS.map((option) => {
                  const isSelected = option.value === selectedMode.value
                  return (
                    <button
                      key={option.value}
                      type="button"
                      className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors ${
                        isSelected
                          ? 'bg-primary/15 text-primary'
                          : 'text-on-surface/80 hover:bg-surface-container-highest'
                      }`}
                      onClick={() => {
                        onChatModeChange(option.value)
                        setIsModeMenuOpen(false)
                      }}
                    >
                      <span className="material-symbols-outlined text-[18px]">
                        {option.icon}
                      </span>
                      <span className="font-medium">{option.label}</span>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )}

        <label className="sr-only" htmlFor={inputId}>
          Chat message
        </label>
        <input
          id={inputId}
          ref={inputRef}
          className="flex-1 bg-transparent px-2 py-3 font-body text-sm text-on-surface outline-none placeholder:text-on-surface/40"
          placeholder={placeholder}
          value={value}
          disabled={disabled}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submitMessage()
            }
          }}
        />

        <button
          type="button"
          className="relative flex-shrink-0 overflow-hidden rounded-xl bg-gradient-to-br from-primary to-primary-container p-3 text-surface-container-lowest shadow-[0_0_20px_rgba(59,191,250,0.20)] transition-all hover:shadow-[0_0_30px_rgba(59,191,250,0.40)]"
          aria-label="Send message"
          disabled={disabled}
          onClick={submitMessage}
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

      <div className="mt-3 text-center text-[10px] font-semibold uppercase tracking-widest text-on-surface/30">
        Kinetic Vault AI generates predictive models. Verify critical outputs.
      </div>
    </div>
  )
}

