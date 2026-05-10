import type { ChatMode } from '../../types/api'

const MODE_OPTIONS: { value: ChatMode; label: string; icon: string }[] = [
  { value: 'auto', label: 'Auto', icon: 'auto_awesome' },
  { value: 'rag', label: 'RAG', icon: 'database' },
  { value: 'web', label: 'Web', icon: 'language' },
]

export function ChatModeSelector({
  mode,
  onChange,
  disabled = false,
}: {
  mode: ChatMode
  onChange: (mode: ChatMode) => void
  disabled?: boolean
}) {
  return (
    <div className="flex items-center gap-1 rounded-xl bg-surface-container/60 p-0.5">
      {MODE_OPTIONS.map((opt) => {
        const isActive = mode === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            disabled={disabled}
            onClick={() => onChange(opt.value)}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all duration-200 ${
              isActive
                ? 'bg-primary/15 text-primary shadow-sm'
                : 'text-on-surface/50 hover:bg-surface-container-high hover:text-on-surface/80'
            } ${disabled ? 'pointer-events-none opacity-50' : ''}`}
          >
            <span className="material-symbols-outlined text-[16px]">
              {opt.icon}
            </span>
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
