import { useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

type Pattern = { pattern: string; count: number; suggested_fix: string }

/** Failure insights from GET /api/insights/failures — poll 3s. */
export function FailureInsightsPage() {
  const [patterns, setPatterns] = useState<Pattern[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const r = await apiFetch('/api/insights/failures')
      if (!r.ok) throw new Error(await r.text())
      const j = (await r.json()) as { patterns: Pattern[] }
      setPatterns(j.patterns ?? [])
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Load failed')
    }
  }, [])

  useEffect(() => {
    void load()
    const t = window.setInterval(() => void load(), 3000)
    return () => window.clearInterval(t)
  }, [load])

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-[var(--color-agentos-border)] bg-[var(--color-agentos-surface)]/80 px-8 py-6 backdrop-blur-sm">
        <h1 className="text-xl font-semibold tracking-tight">Failure insights</h1>
        <p className="mt-1 text-sm text-[var(--color-agentos-muted)]">
          Aggregated failure patterns across runs (refreshed every 3s).
        </p>
      </header>
      <main className="flex-1 px-8 py-6">
        {error && (
          <p className="mb-4 text-sm text-red-400" role="alert">
            {error}
          </p>
        )}
        <div className="space-y-3">
          {patterns.length === 0 && !error && (
            <p className="font-mono text-sm text-[var(--color-agentos-muted)]">
              No failure patterns yet.
            </p>
          )}
          {patterns.map((p) => (
            <div
              key={p.pattern}
              className="rounded-lg border border-[var(--color-agentos-border)] bg-[var(--color-agentos-surface)] p-4"
            >
              <div className="font-mono text-sm text-[var(--color-agentos-fg)]">
                {p.pattern}
              </div>
              <div className="mt-1 text-xs text-[var(--color-agentos-muted)]">
                Count: {p.count}
              </div>
              <div className="mt-2 text-sm text-[var(--color-agentos-accent)]">
                Suggested fix: {p.suggested_fix}
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
