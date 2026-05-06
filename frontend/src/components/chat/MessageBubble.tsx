import type { ChatMessage } from '../../types/chat'

function Avatar({ role }: { role: ChatMessage['role'] }) {
  if (role === 'user') {
    return (
      <div className="h-10 w-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
        <span className="material-symbols-outlined text-primary text-[20px]">
          person
        </span>
      </div>
    )
  }

  return (
    <div className="h-10 w-10 rounded-xl bg-surface-container-highest border border-outline-variant/10 shadow-[0_4px_30px_rgba(0,0,0,0.20)] flex items-center justify-center flex-shrink-0">
      <span
        className="material-symbols-outlined text-primary text-[20px]"
        style={{ fontVariationSettings: "'FILL' 1" }}
      >
        generating_tokens
      </span>
    </div>
  )
}

function ActionButton({
  icon,
  label,
  right,
}: {
  icon: string
  label: string
  right?: boolean
}) {
  return (
    <button
      className={[
        'text-[11px] font-semibold uppercase tracking-wider transition-colors flex items-center gap-1',
        right
          ? 'text-on-surface/60 hover:text-on-surface ml-auto'
          : 'text-primary hover:text-primary-dim',
      ].join(' ')}
      type="button"
    >
      <span className="material-symbols-outlined text-[14px]">{icon}</span>
      {label}
    </button>
  )
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  const isLuminary = message.variant === 'luminary'

  return (
    <div
      className={[
        'flex gap-4',
        isUser ? 'self-end flex-row-reverse max-w-3xl' : 'max-w-4xl',
      ].join(' ')}
    >
      <Avatar role={message.role} />

      <div
        className={[
          'flex flex-col gap-1.5 mt-1',
          isUser ? 'items-end' : 'w-full',
        ].join(' ')}
      >
        <span
          className={[
            'text-[11px] font-semibold uppercase tracking-wider text-on-surface/60',
            isUser ? 'pr-1' : 'pl-1',
          ].join(' ')}
        >
          {message.authorLabel}
        </span>

        {!isLuminary && (
          <div
            className={[
              'rounded-2xl px-6 py-4 text-sm leading-relaxed',
              isUser
                ? 'bg-surface-container-high rounded-tr-sm shadow-[0_4px_30px_rgba(0,0,0,0.30)]'
                : 'bg-surface-container-low rounded-tl-sm',
            ].join(' ')}
          >
            {message.text}
          </div>
        )}

        {isLuminary && (
          <div className="relative overflow-hidden rounded-2xl rounded-tl-sm bg-surface-container-highest border border-outline-variant/10">
            <div className="pointer-events-none absolute left-0 top-0 h-64 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/10 blur-[60px]" />

            <div className="relative z-10 p-6">
              <h3 className="mb-4 flex items-center gap-2 font-headline text-lg font-bold text-on-surface">
                <span className="material-symbols-outlined text-primary text-[18px]">
                  hub
                </span>
                {message.title ?? 'Synthesis Complete'}
              </h3>

              <p className="mb-6 text-sm leading-relaxed text-on-surface/80">
                {message.text}
              </p>

              {!!message.bento?.length && (
                <div className="grid grid-cols-2 gap-4">
                  {message.bento.slice(0, 2).map((item) => (
                    <div
                      key={item.label}
                      className="rounded-xl bg-surface-container-low p-4 border border-outline-variant/5"
                    >
                      <span className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-on-surface/60">
                        {item.label}
                      </span>
                      <span className="text-sm font-medium text-on-surface">
                        {item.value}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {!!message.actions?.length && (
              <div className="relative z-10 flex gap-3 bg-surface-container-low/50 px-6 py-3 border-t border-outline-variant/5">
                {message.actions.map((a) => (
                  <ActionButton
                    key={a.id}
                    icon={a.icon}
                    label={a.label}
                    right={a.align === 'right'}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

