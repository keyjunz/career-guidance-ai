export function ChatHeader() {
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

      <div className="flex gap-4">
        <button className="h-10 w-10 rounded-xl bg-surface-container-low flex items-center justify-center text-on-surface/60 transition-colors hover:bg-surface-container-high hover:text-on-surface">
          <span className="material-symbols-outlined text-[20px]">search</span>
        </button>
        <button className="h-10 w-10 rounded-xl bg-surface-container-low flex items-center justify-center text-on-surface/60 transition-colors hover:bg-surface-container-high hover:text-on-surface">
          <span className="material-symbols-outlined text-[20px]">tune</span>
        </button>
      </div>
    </header>
  )
}

