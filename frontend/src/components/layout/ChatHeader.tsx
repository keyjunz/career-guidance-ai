import type { AuthUser } from '../../types/api'

type ChatHeaderProps = {
  user?: AuthUser | null
  onLogout?: () => void
  theme?: 'light' | 'dark'
  onToggleTheme?: () => void
}

export function ChatHeader({
  user,
  onLogout,
  theme = 'light',
  onToggleTheme,
}: ChatHeaderProps) {
  const isDark = theme === 'dark'

  return (
    <header className="flex-shrink-0 px-10 py-8 flex items-center justify-between z-20">
      <div className="flex flex-col gap-1">
        <h2 className="font-headline text-2xl font-extrabold tracking-tight text-on-surface">
          RAG Assistant
        </h2>
        <div className="flex items-center gap-2">
          <span className="relative h-2 w-2 rounded-full bg-primary shadow-[0_0_10px_rgba(59,191,250,0.80)]">
            <span className="absolute inset-0 rounded-full bg-primary animate-ping opacity-50" />
          </span>
          <span className="text-xs font-semibold uppercase tracking-widest text-primary-dim">
            Secure &amp; Online
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {user && (
          <div className="hidden text-right sm:block">
            <p className="text-sm font-semibold text-on-surface">{user.user_name}</p>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-primary-dim">
              {user.role}
            </p>
          </div>
        )}
        <button className="h-10 w-10 rounded-xl bg-surface-container-low flex items-center justify-center text-on-surface/60 transition-colors hover:bg-surface-container-high hover:text-on-surface">
          <span className="material-symbols-outlined text-[20px]">search</span>
        </button>
        <button
          className="h-10 w-10 rounded-xl bg-surface-container-low flex items-center justify-center text-on-surface/65 transition-colors hover:bg-surface-container-high hover:text-on-surface"
          onClick={onToggleTheme}
          type="button"
          aria-label="Toggle color theme"
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          <span className="material-symbols-outlined text-[20px]">
            {isDark ? 'light_mode' : 'dark_mode'}
          </span>
        </button>
        <button
          className="h-10 rounded-xl bg-surface-container-low px-4 text-xs font-bold uppercase tracking-wider text-on-surface/60 transition-colors hover:bg-surface-container-high hover:text-on-surface"
          onClick={onLogout}
          type="button"
        >
          Logout
        </button>
      </div>
    </header>
  )
}

