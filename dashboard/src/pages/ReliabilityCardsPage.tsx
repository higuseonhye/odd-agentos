import { useState } from 'react'
import { apiFetch } from '../lib/api'

/** Reliability card from GET /api/reliability/:agent_name */
export function ReliabilityCardsPage() {
  const [agent, setAgent] = useState('support_bot')
  const [days, setDays] = useState(30)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [card, setCard] = useState<Record<string, unknown> | null>(null)

  async function loadCard(nameOverride?: string) {
    const name = nameOverride ?? agent
    if (nameOverride !== undefined) {
      setAgent(nameOverride)
    }
    setLoading(true)
    setError(null)
    setCard(null)
    try {
      const r = await apiFetch(
        `/api/reliability/${encodeURIComponent(name)}?days=${days}`,
      )
      if (!r.ok) throw new Error(await r.text())
      setCard((await r.json()) as Record<string, unknown>)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-[var(--color-agentos-border)] bg-[var(--color-agentos-surface)]/80 px-8 py-6 backdrop-blur-sm">
        <h1 className="text-xl font-semibold tracking-tight">Reliability cards</h1>
        <p className="mt-1 text-sm text-[var(--color-agentos-muted)]">
          Trust score and metrics for an agent over a rolling window. After{' '}
          <code className="font-mono text-xs">python scripts/seed_demo_data.py</code>, try{' '}
          <code className="font-mono text-xs">support_bot</code> or{' '}
          <code className="font-mono text-xs">ledger_analyst</code>.
        </p>
      </header>
      <main className="flex-1 px-8 py-6">
        <div className="mb-6 flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-[var(--color-agentos-muted)]">Agent</span>
            <input
              type="text"
              value={agent}
              onChange={(e) => setAgent(e.target.value)}
              className="rounded-md border border-[var(--color-agentos-border)] bg-[var(--color-agentos-elevated)] px-3 py-2 font-mono text-sm"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-[var(--color-agentos-muted)]">Days</span>
            <input
              type="number"
              value={days}
              min={1}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-24 rounded-md border border-[var(--color-agentos-border)] bg-[var(--color-agentos-elevated)] px-3 py-2 font-mono text-sm"
            />
          </label>
          <button
            type="button"
            disabled={loading}
            onClick={() => void loadCard()}
            className="rounded-md bg-[var(--color-agentos-accent)] px-4 py-2 text-sm font-medium text-[var(--color-agentos-bg)] disabled:opacity-50"
          >
            {loading ? 'Loading…' : 'Load card'}
          </button>
          <div className="flex flex-wrap gap-2">
            <span className="self-center text-xs text-[var(--color-agentos-muted)]">Presets:</span>
            {(['support_bot', 'ledger_analyst'] as const).map((a) => (
              <button
                key={a}
                type="button"
                className="rounded-md border border-[var(--color-agentos-border)] px-2 py-1 font-mono text-xs text-[var(--color-agentos-fg)]"
                onClick={() => void loadCard(a)}
              >
                {a}
              </button>
            ))}
          </div>
        </div>
        {error && (
          <p className="mb-4 text-sm text-red-400" role="alert">
            {error}
          </p>
        )}
        {card && (
          <div className="rounded-lg border border-[var(--color-agentos-border)] bg-[var(--color-agentos-surface)] p-6">
            <div className="mb-4 flex flex-wrap gap-6">
              <div>
                <p className="text-xs text-[var(--color-agentos-muted)]">Trust score</p>
                <p className="font-mono text-3xl text-[var(--color-agentos-accent)]">
                  {String(card.trust_score ?? '—')}
                </p>
              </div>
              <div>
                <p className="text-xs text-[var(--color-agentos-muted)]">Level</p>
                <p className="font-mono text-lg">{String(card.trust_level ?? '—')}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--color-agentos-muted)]">Period</p>
                <p className="font-mono text-sm">{String(card.period ?? '')}</p>
              </div>
            </div>
            <div className="mb-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => {
                  const blob = new Blob([JSON.stringify(card, null, 2)], {
                    type: 'application/json',
                  })
                  const a = document.createElement('a')
                  a.href = URL.createObjectURL(blob)
                  a.download = `reliability-${agent}-${new Date().toISOString().slice(0, 10)}.json`
                  a.click()
                  URL.revokeObjectURL(a.href)
                }}
                className="rounded-md border border-[var(--color-agentos-border)] px-3 py-1.5 text-xs text-[var(--color-agentos-fg)]"
              >
                Download JSON
              </button>
            </div>
            <pre className="max-h-96 overflow-auto font-mono text-xs leading-relaxed text-[var(--color-agentos-muted)]">
              {JSON.stringify(card, null, 2)}
            </pre>
            <p className="mt-4 text-xs text-[var(--color-agentos-muted)]">
              Server also persists under <code className="font-mono">reports/</code>.
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
