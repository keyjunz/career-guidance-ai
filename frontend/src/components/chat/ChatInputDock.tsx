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
  isStreaming = false,
  onStop,
  chatMode = 'auto',
  onChatModeChange,
}: {
  placeholder: string
  onSend: (text: string) => void
  disabled?: boolean
  isStreaming?: boolean
  onStop?: () => void
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
    <div className="pointer-events-none absolute bottom-0 left-0 right-0 z-30 px-4 pb-5 pt-10 sm:px-6">
      <div className="pointer-events-auto mx-auto w-full max-w-[46rem]">
        <div className="composer-pill px-1.5 py-1 transition sm:px-2 sm:py-1.5">
          <div className="flex items-center gap-0.5 sm:gap-1.5">
            {onChatModeChange && (
              <div className="relative flex-shrink-0" ref={modeMenuRef}>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => setIsModeMenuOpen((prev) => !prev)}
                  className={[
                    'u-focus flex items-center gap-1.5 rounded-full px-2.5 py-2 text-on-surface/75 transition disabled:opacity-45 sm:px-3',
                    isModeMenuOpen
                      ? 'bg-surface-container text-on-surface'
                      : 'hover:bg-surface-container/80',
                  ].join(' ')}
                  aria-expanded={isModeMenuOpen}
                  aria-haspopup="listbox"
                  aria-label="Chat mode"
                >
                  <span
                    className="material-symbols-outlined text-[19px] text-primary/90"
                    style={{ fontVariationSettings: "'FILL' 0" }}
                  >
                    {selectedMode.icon}
                  </span>
                  <span className="hidden text-[13px] font-medium sm:inline">
                    {selectedMode.label}
                  </span>
                  <span className="material-symbols-outlined text-[18px] text-on-surface/38">
                    {isModeMenuOpen ? 'expand_less' : 'expand_more'}
                  </span>
                </button>

                {isModeMenuOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-40 bg-black/20 sm:hidden"
                      aria-hidden
                      onClick={() => setIsModeMenuOpen(false)}
                    />
                    <div
                      className="chat-mode-menu-popover absolute bottom-[calc(100%+10px)] left-0 z-50 w-[min(calc(100vw-2rem),15.5rem)] p-1.5 sm:left-0 sm:w-[15.5rem]"
                      role="listbox"
                      aria-label="Chọn chế độ trả lời"
                    >
                      <div className="flex flex-col gap-0.5">
                        {CHAT_MODE_OPTIONS.map((option) => {
                          const isSelected = option.value === selectedMode.value
                          return (
                            <button
                              key={option.value}
                              type="button"
                              role="option"
                              aria-selected={isSelected}
                              className={[
                                'u-focus flex min-h-[2.75rem] w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-[13px] transition',
                                isSelected
                                  ? 'bg-primary/10 font-medium text-on-surface'
                                  : 'text-on-surface/72 hover:bg-surface-container',
                              ].join(' ')}
                              onClick={() => {
                                onChatModeChange(option.value)
                                setIsModeMenuOpen(false)
                              }}
                            >
                              <span
                                className={[
                                  'material-symbols-outlined shrink-0 text-[20px]',
                                  isSelected ? 'text-primary' : 'text-on-surface/42',
                                ].join(' ')}
                                style={
                                  isSelected
                                    ? { fontVariationSettings: "'FILL' 1" }
                                    : { fontVariationSettings: "'FILL' 0" }
                                }
                              >
                                {option.icon}
                              </span>
                              <span className="min-w-0 flex-1 leading-snug">
                                {option.label}
                              </span>
                              {isSelected ? (
                                <span
                                  className="material-symbols-outlined shrink-0 text-[18px] text-primary"
                                  style={{ fontVariationSettings: "'FILL' 1" }}
                                >
                                  check
                                </span>
                              ) : null}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            <label className="sr-only" htmlFor={inputId}>
              Chat message
            </label>
            <input
              id={inputId}
              ref={inputRef}
              className="u-focus min-h-[46px] flex-1 bg-transparent px-2 py-2.5 font-body text-[15px] text-on-surface outline-none placeholder:text-on-surface/36 sm:min-h-[48px] sm:px-3"
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

            {isStreaming && onStop ? (
              <button
                type="button"
                className="u-focus mr-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-on-surface/14 bg-surface-container-high text-on-surface shadow-sm transition hover:bg-surface-container sm:h-11 sm:w-11"
                aria-label="Dừng tạo câu trả lời"
                onClick={onStop}
              >
                <span
                  className="material-symbols-outlined text-[22px]"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  stop
                </span>
              </button>
            ) : null}

            <button
              type="button"
              className="u-focus mr-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-white shadow-md transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-38 sm:h-11 sm:w-11"
              aria-label="Send message"
              disabled={disabled || !value.trim()}
              onClick={submitMessage}
            >
              <span
                className="material-symbols-outlined text-[21px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                arrow_upward
              </span>
            </button>
          </div>
        </div>

        <p className="pointer-events-auto mt-2.5 text-center text-[10px] font-medium leading-snug text-on-surface/32">
          Trợ lý AI có thể sai — hãy kiểm tra quyết định quan trọng.
        </p>
      </div>
    </div>
  )
}
