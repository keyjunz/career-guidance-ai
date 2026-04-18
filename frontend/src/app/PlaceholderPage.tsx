export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="min-h-screen bg-surface text-on-surface grid place-items-center">
      <div className="bg-surface-container-high rounded-2xl px-6 py-5">
        <div className="font-headline text-xl font-extrabold">{title}</div>
        <div className="mt-2 text-sm text-on-surface/70">
          Placeholder page. Not implemented in this phase.
        </div>
      </div>
    </div>
  )
}

