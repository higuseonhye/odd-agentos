import { NavLink, Outlet } from 'react-router-dom'
import { API_BASE } from '../../lib/api'

const nav: readonly {
  to: string
  label: string
  end?: boolean
}[] = [
  { to: '/', label: 'Runs', end: true },
  { to: '/insights', label: 'Failure insights' },
  { to: '/policies', label: 'Policies' },
  { to: '/reliability', label: 'Reliability' },
]

export function AppShell() {
  return (
    <div className="flex min-h-dvh bg-[var(--color-agentos-bg)] text-[var(--color-agentos-fg)]">
      <aside className="flex w-56 shrink-0 flex-col border-r border-[var(--color-agentos-border)] bg-[var(--color-agentos-surface)]">
        <div className="border-b border-[var(--color-agentos-border)] px-4 py-5">
          <div className="font-mono text-sm font-medium tracking-tight text-[var(--color-agentos-accent)]">
            AgentOS
          </div>
          <p className="mt-1 text-xs text-[var(--color-agentos-muted)]">
            Agent control plane
          </p>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 p-2" aria-label="Main">
          {nav.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end ?? false}
              className={({ isActive }) =>
                [
                  'rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-[var(--color-agentos-accent-dim)] text-[var(--color-agentos-accent)]'
                    : 'text-[var(--color-agentos-muted)] hover:bg-[var(--color-agentos-elevated)] hover:text-[var(--color-agentos-fg)]',
                ].join(' ')
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-[var(--color-agentos-border)] p-3">
          <p className="font-mono text-[10px] leading-relaxed text-[var(--color-agentos-muted)]">
            API:{' '}
            <span className="break-all text-[var(--color-agentos-fg)]/80">
              {API_BASE || '(same origin)'}
            </span>
          </p>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <Outlet />
      </div>
    </div>
  )
}
