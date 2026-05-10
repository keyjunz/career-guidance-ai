import type { AuthUser } from '../../types/api'

type ChatHeaderProps = {
  user?: AuthUser | null
  conversationTitle?: string
  onLogout?: () => void
  theme?: 'light' | 'dark'
  onToggleTheme?: () => void
}

export function ChatHeader({
  user,
  conversationTitle,
  onLogout,
  theme = 'light',
  onToggleTheme,
}: ChatHeaderProps) {
  const isDark = theme === 'dark'
  const title =
    conversationTitle?.trim() ||
    'Kinetic Assistant'

  return (
    <header className="sticky top-0 z-20 flex flex-shrink-0 items-center gap-3 bg-background/80 px-4 py-2.5 backdrop-blur-md sm:px-5 sm:py-3">
      <div className="min-w-0 flex-1 sm:max-w-[33%]" />

      <div className="min-w-0 max-w-[min(100%,28rem)] flex-1 text-center">
        <h2 className="font-headline truncate text-sm font-semibold tracking-tight text-on-surface sm:text-[15px]">
          {title}
        </h2>
        <div className="mt-0.5 hidden items-center justify-center gap-1.5 sm:flex">
          <span
            className="h-1 w-1 shrink-0 rounded-full bg-primary/85"
            aria-hidden
          />
          <span className="text-[10px] font-medium text-on-surface/40">
            Sẵn sàng
          </span>
        </div>
      </div>

      <div className="flex min-w-0 flex-1 shrink-0 items-center justify-end gap-1 sm:max-w-[33%] sm:gap-2">
        {user && (
          <div className="hidden max-w-[140px] text-right sm:block">
            <p className="truncate text-xs font-medium text-on-surface">
              {user.user_name}
            </p>
            <p className="truncate text-[10px] font-medium uppercase tracking-wider text-on-surface/40">
              {user.role}
            </p>
          </div>
        )}
        <button
          className="u-focus flex h-9 w-9 items-center justify-center rounded-full border border-transparent text-on-surface/45 transition hover:bg-surface-container-high hover:text-on-surface"
          type="button"
          aria-label="Search"
          title="Search"
        >
          <span className="material-symbols-outlined text-[19px]">search</span>
        </button>
        <button
          className="u-focus flex h-9 w-9 items-center justify-center rounded-full border border-transparent text-on-surface/50 transition hover:bg-surface-container-high hover:text-on-surface"
          onClick={onToggleTheme}
          type="button"
          aria-label="Toggle color theme"
          title={isDark ? 'Light mode' : 'Dark mode'}
        >
          <span className="material-symbols-outlined text-[19px]">
            {isDark ? 'light_mode' : 'dark_mode'}
          </span>
        </button>
        <button
          className="u-focus hidden rounded-full bg-surface-container-high px-4 py-2 text-[11px] font-semibold text-on-surface/75 transition hover:bg-surface-container sm:inline"
          onClick={onLogout}
          type="button"
        >
          Log out
        </button>
        <button
          className="u-focus flex h-9 w-9 items-center justify-center rounded-full bg-surface-container-high text-on-surface/65 sm:hidden"
          onClick={onLogout}
          type="button"
          aria-label="Log out"
        >
          <span className="material-symbols-outlined text-[19px]">logout</span>
        </button>
      </div>
    </header>
  )
}
