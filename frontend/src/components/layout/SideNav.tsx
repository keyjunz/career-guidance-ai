const NavItem = ({
  icon,
  label,
  active,
}: {
  icon: string
  label: string
  active?: boolean
}) => {
  return (
    <a
      href="#"
      className={[
        'mx-2 my-1 flex items-center gap-3 rounded-lg px-4 py-3 transition-all duration-300 ease-out',
        active
          ? 'bg-gradient-to-r from-sky-500 to-sky-600 text-white shadow-[0_0_15px_rgba(56,189,248,0.30)]'
          : 'text-slate-500 hover:text-slate-200 hover:bg-[#1e293b]',
      ].join(' ')}
    >
      <span
        className="material-symbols-outlined text-[20px]"
        style={
          active
            ? ({ fontVariationSettings: "'FILL' 1" } as React.CSSProperties)
            : undefined
        }
      >
        {icon}
      </span>
      <span className="text-sm font-medium">{label}</span>
    </a>
  )
}

export function SideNav() {
  return (
    <nav className="fixed left-0 top-0 z-50 flex h-full w-72 flex-col overflow-y-auto rounded-r-2xl bg-[#0c1324] py-8 shadow-[4px_0_40px_rgba(0,0,0,0.30)]">
      <div className="px-8 mb-8">
        <h1 className="font-headline text-lg font-bold tracking-tight text-sky-400 mb-1">
          Kinetic Assistant
        </h1>
        <p className="font-body text-sm text-on-surface/70">
          High-Security Sanctuary
        </p>
      </div>

      <div className="px-6 mb-8">
        <button className="w-full rounded-xl bg-gradient-to-r from-primary to-primary-container py-3 px-4 font-headline text-sm font-bold text-white shadow-[0_0_15px_rgba(59,191,250,0.30)] transition-transform duration-200 active:scale-95">
          <span className="inline-flex items-center justify-center gap-2">
            <span className="material-symbols-outlined text-[18px]">add</span>
            New Chat
          </span>
        </button>
      </div>

      <div className="flex-1 px-4 flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <p className="px-4 mb-2 text-[10px] font-semibold uppercase tracking-widest text-on-surface/60">
            Active Vectors
          </p>
          <NavItem icon="history" label="Recent Analysis" active />
          <NavItem icon="auto_awesome" label="Project Genesis" />
          <NavItem icon="inventory_2" label="Research Vault" />
          <NavItem icon="folder_open" label="Archive" />
        </div>
      </div>

      <div className="px-4 mt-auto pt-6 relative">
        <div className="absolute left-8 right-8 top-0 h-px bg-outline-variant/10" />
        <a
          href="#"
          className="mx-2 flex items-center gap-3 rounded-lg px-4 py-2 text-slate-500 transition-all hover:bg-[#1e293b] hover:text-slate-200"
        >
          <span className="material-symbols-outlined text-[18px]">shield</span>
          <span className="text-sm font-medium">Security</span>
        </a>
        <a
          href="#"
          className="mx-2 flex items-center gap-3 rounded-lg px-4 py-2 text-slate-500 transition-all hover:bg-[#1e293b] hover:text-slate-200"
        >
          <span className="material-symbols-outlined text-[18px]">person</span>
          <span className="text-sm font-medium">Profile Settings</span>
        </a>

        <div className="mt-4 mx-2 flex items-center gap-3 rounded-xl bg-surface-container-high px-4 py-3 border border-outline-variant/10">
          <div className="w-8 h-8 rounded-full bg-primary-container/20 flex items-center justify-center flex-shrink-0 text-primary">
            <span className="font-headline text-xs font-bold">JD</span>
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-on-surface">
              John Doe
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-primary-dim">
              Admin OCR
            </span>
          </div>
        </div>
      </div>
    </nav>
  )
}

