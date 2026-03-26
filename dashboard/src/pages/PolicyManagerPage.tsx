import { useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

/** Policy YAML editor + dry-run evaluate. */
export function PolicyManagerPage() {
  const [raw, setRaw] = useState('')
  const [path, setPath] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [dryJson, setDryJson] = useState(
    '{"step_id":"dry","agent_name":"greeter","agent_tags":[],"risk_level":"low","tool_calls_per_minute":0}',
  )
  const [dryResult, setDryResult] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const r = await apiFetch('/api/policies')
      if (!r.ok) throw new Error(await r.text())
      const j = (await r.json()) as { raw?: string; path?: string }
      setRaw(j.raw ?? '')
      setPath(j.path ?? '')
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Load failed')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function save() {
    setSaved(false)
    try {
      const r = await apiFetch('/api/policies', {
        method: 'PUT',
        body: JSON.stringify({ raw }),
      })
      if (!r.ok) throw new Error(await r.text())
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    }
  }

  async function dryRun() {
    setDryResult(null)
    try {
      const step = JSON.parse(dryJson) as Record<string, unknown>
      const r = await apiFetch('/api/policies/evaluate', {
        method: 'POST',
        body: JSON.stringify({ step: { ...step } }),
      })
      if (!r.ok) throw new Error(await r.text())
      const j = await r.json()
      setDryResult(JSON.stringify(j, null, 2))
    } catch (e) {
      setDryResult(e instanceof Error ? e.message : 'Invalid JSON or request failed')
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-[var(--color-agentos-border)] bg-[var(--color-agentos-surface)]/80 px-8 py-6 backdrop-blur-sm">
        <h1 className="text-xl font-semibold tracking-tight">Policy manager</h1>
        <p className="mt-1 text-sm text-[var(--color-agentos-muted)]">
          {path && (
            <span className="font-mono text-xs text-[var(--color-agentos-fg)]/80">
              {path}
            </span>
          )}
        </p>
      </header>
      <main className="grid flex-1 gap-6 px-8 py-6 lg:grid-cols-2">
        <section className="flex min-h-[320px] flex-col">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-medium text-[var(--color-agentos-muted)]">YAML</h2>
            <button
              type="button"
              onClick={() => void save()}
              className="rounded-md bg-[var(--color-agentos-accent)] px-3 py-1.5 text-xs font-medium text-[var(--color-agentos-bg)]"
            >
              Save
            </button>
          </div>
          {error && (
            <p className="mb-2 text-sm text-red-400" role="alert">
              {error}
            </p>
          )}
          {saved && (
            <p className="mb-2 text-sm text-emerald-400">Saved.</p>
          )}
          <textarea
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
            className="min-h-[280px] flex-1 resize-y rounded-lg border border-[var(--color-agentos-border)] bg-[var(--color-agentos-bg)] p-4 font-mono text-sm text-[var(--color-agentos-fg)]"
            spellCheck={false}
          />
        </section>
        <section>
          <h2 className="mb-2 text-sm font-medium text-[var(--color-agentos-muted)]">
            Test policy (dry-run)
          </h2>
          <p className="mb-2 text-sm text-[var(--color-agentos-muted)]">
            POST body: <code className="text-xs">{'{ "step": { ... } }'}</code> — edit JSON
            for hypothetical step.
          </p>
          <textarea
            value={dryJson}
            onChange={(e) => setDryJson(e.target.value)}
            className="mb-3 min-h-[120px] w-full rounded-lg border border-[var(--color-agentos-border)] bg-[var(--color-agentos-bg)] p-3 font-mono text-xs"
            spellCheck={false}
          />
          <button
            type="button"
            onClick={() => void dryRun()}
            className="rounded-md border border-[var(--color-agentos-border)] bg-[var(--color-agentos-elevated)] px-3 py-2 text-sm"
          >
            Evaluate
          </button>
          {dryResult && (
            <pre className="mt-4 max-h-64 overflow-auto rounded-lg border border-[var(--color-agentos-border)] bg-[var(--color-agentos-surface)] p-3 font-mono text-xs text-[var(--color-agentos-fg)]">
              {dryResult}
            </pre>
          )}
        </section>
      </main>
    </div>
  )
}
