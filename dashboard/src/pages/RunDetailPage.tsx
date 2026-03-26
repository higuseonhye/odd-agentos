import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../lib/api'
import type { RunDetailResponse, StepRow } from '../types/api'

function StepIcon({ status }: { status: string }) {
  if (status === 'pending_approval') return <span title="Pending">🟡</span>
  if (status === 'failed' || status === 'policy_blocked') return <span title="Failed">🔴</span>
  if (status === 'completed') return <span title="Done">✅</span>
  if (status === 'running') return <span title="Running">⏳</span>
  return <span title="Pending">⚪</span>
}

/** Run detail: timeline, approve/deny, audit log — polling 3s. */
export function RunDetailPage() {
  const { run_id } = useParams<{ run_id: string }>()
  const [data, setData] = useState<RunDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [panel, setPanel] = useState<'step' | 'audit' | 'mri'>('audit')
  const [diagnosis, setDiagnosis] = useState<Record<string, unknown> | null>(null)
  const [diagLoading, setDiagLoading] = useState(false)

  const load = useCallback(async () => {
    if (!run_id) return
    setError(null)
    try {
      const r = await apiFetch(`/api/runs/${encodeURIComponent(run_id)}`)
      if (r.status === 404) {
        setData(null)
        setError('Run not found')
        return
      }
      if (!r.ok) throw new Error(await r.text())
      const j = (await r.json()) as RunDetailResponse
      setData(j)
      setSelectedId((prev) => prev ?? (j.steps?.[0]?.id ?? null))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Load failed')
    } finally {
      setLoading(false)
    }
  }, [run_id])

  useEffect(() => {
    void load()
    const t = window.setInterval(() => void load(), 3000)
    return () => window.clearInterval(t)
  }, [load])

  const state = data?.state as Record<string, unknown> | undefined
  const status = (state?.status as string) ?? '—'
  const pending = state?.pending_step_id as string | undefined
  const selected: StepRow | undefined = data?.steps?.find((s) => s.id === selectedId)

  async function submitApproval(deny: boolean) {
    if (!run_id || !pending) return
    const path = deny
      ? `/api/runs/${encodeURIComponent(run_id)}/deny/${encodeURIComponent(pending)}`
      : `/api/runs/${encodeURIComponent(run_id)}/approve/${encodeURIComponent(pending)}`
    await apiFetch(path, { method: 'POST' })
    void load()
  }

  async function retryRun() {
    if (!run_id) return
    const r = await apiFetch(`/api/runs/${encodeURIComponent(run_id)}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    if (!r.ok) {
      try {
        const j = (await r.json()) as { error?: string }
        setError(j.error ?? `HTTP ${r.status}`)
      } catch {
        setError('Retry failed')
      }
      return
    }
    const j = (await r.json()) as { run_id: string }
    window.location.href = `/runs/${encodeURIComponent(j.run_id)}`
  }

  async function loadDiagnosis() {
    if (!run_id) return
    setDiagLoading(true)
    setError(null)
    try {
      const r = await apiFetch(`/api/runs/${encodeURIComponent(run_id)}/diagnosis`)
      if (!r.ok) throw new Error(await r.text())
      setDiagnosis((await r.json()) as Record<string, unknown>)
      setPanel('mri')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Diagnosis failed')
    } finally {
      setDiagLoading(false)
    }
  }

  async function replayFromStep(stepId: string) {
    if (!run_id) return
    const r = await apiFetch(`/api/runs/${encodeURIComponent(run_id)}/replay`, {
      method: 'POST',
      body: JSON.stringify({ from_step: stepId }),
    })
    if (!r.ok) return
    const j = (await r.json()) as { run_id: string }
    window.location.href = `/runs/${encodeURIComponent(j.run_id)}`
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-[var(--color-agentos-border)] bg-[var(--color-agentos-surface)]/80 px-8 py-6 backdrop-blur-sm">
        <Link
          to="/"
          className="mb-3 inline-flex text-sm text-[var(--color-agentos-accent)] hover:underline"
        >
          ← Runs
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-mono text-lg font-semibold tracking-tight">
              {run_id ?? '—'}
            </h1>
            <p className="mt-1 text-sm text-[var(--color-agentos-muted)]">
              Status:{' '}
              <span className="font-mono text-[var(--color-agentos-fg)]">{status}</span>
              {error && (
                <span className="ml-2 text-red-400" role="alert">
                  {error}
                </span>
              )}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {pending && (
              <>
                <button
                  type="button"
                  onClick={() => void submitApproval(false)}
                  className="rounded-md bg-emerald-600/90 px-3 py-2 text-sm text-white hover:bg-emerald-600"
                >
                  Approve
                </button>
                <button
                  type="button"
                  onClick={() => void submitApproval(true)}
                  className="rounded-md bg-red-600/90 px-3 py-2 text-sm text-white hover:bg-red-600"
                >
                  Deny
                </button>
              </>
            )}
            <button
              type="button"
              onClick={() => void retryRun()}
              className="rounded-md border border-[var(--color-agentos-border)] bg-[var(--color-agentos-elevated)] px-3 py-2 text-sm text-[var(--color-agentos-fg)] hover:bg-[var(--color-agentos-border)]/50"
            >
              Retry from failure
            </button>
            <button
              type="button"
              disabled={diagLoading}
              onClick={() => void loadDiagnosis()}
              className="rounded-md border border-[var(--color-agentos-accent)]/40 bg-[var(--color-agentos-accent-dim)] px-3 py-2 text-sm text-[var(--color-agentos-accent)] disabled:opacity-50"
            >
              {diagLoading ? 'Diagnosis…' : 'System MRI'}
            </button>
          </div>
        </div>
      </header>

      <div className="grid flex-1 gap-0 lg:grid-cols-[1fr_minmax(280px,400px)]">
        <main className="border-b border-[var(--color-agentos-border)] px-8 py-6 lg:border-b-0 lg:border-r">
          <h2 className="mb-4 text-sm font-medium text-[var(--color-agentos-muted)]">
            Step timeline
          </h2>
          {loading && (
            <p className="font-mono text-sm text-[var(--color-agentos-muted)]">Loading…</p>
          )}
          {!loading && data?.steps && (
            <ul className="space-y-2">
              {data.steps.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(s.id)}
                    className={`flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                      selectedId === s.id
                        ? 'border-[var(--color-agentos-accent)] bg-[var(--color-agentos-accent-dim)]'
                        : 'border-[var(--color-agentos-border)] bg-[var(--color-agentos-surface)] hover:bg-[var(--color-agentos-elevated)]'
                    }`}
                  >
                    <StepIcon status={s.status} />
                    <span className="font-mono text-xs text-[var(--color-agentos-muted)]">
                      {s.id}
                    </span>
                    <span className="text-[var(--color-agentos-muted)]">{s.agent}</span>
                    <span className="ml-auto font-mono text-xs">{s.status}</span>
                  </button>
                  {(s.status === 'failed' || s.status === 'policy_blocked') && (
                    <button
                      type="button"
                      onClick={() => void replayFromStep(s.id)}
                      className="mt-1 ml-10 text-xs text-[var(--color-agentos-accent)] hover:underline"
                    >
                      Replay from here
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </main>
        <aside className="flex flex-col px-8 py-6">
          <div className="mb-4 flex flex-wrap gap-2 border-b border-[var(--color-agentos-border)] pb-2">
            <button
              type="button"
              onClick={() => setPanel('step')}
              className={`text-sm ${panel === 'step' ? 'text-[var(--color-agentos-fg)]' : 'text-[var(--color-agentos-muted)]'}`}
            >
              Step detail
            </button>
            <button
              type="button"
              onClick={() => setPanel('audit')}
              className={`text-sm ${panel === 'audit' ? 'text-[var(--color-agentos-fg)]' : 'text-[var(--color-agentos-muted)]'}`}
            >
              Audit log
            </button>
            <button
              type="button"
              onClick={() => setPanel('mri')}
              className={`text-sm ${panel === 'mri' ? 'text-[var(--color-agentos-fg)]' : 'text-[var(--color-agentos-muted)]'}`}
            >
              Diagnosis
            </button>
          </div>
          {panel === 'step' && selected && (
            <div className="font-mono text-xs leading-relaxed text-[var(--color-agentos-fg)]">
              <p className="text-[var(--color-agentos-muted)]">Agent</p>
              <p className="mb-3">{selected.agent}</p>
              <p className="text-[var(--color-agentos-muted)]">Policy / detail</p>
              <pre className="max-h-48 overflow-auto rounded bg-[var(--color-agentos-bg)] p-2 text-[11px]">
                {JSON.stringify(selected.detail ?? {}, null, 2)}
              </pre>
            </div>
          )}
          {panel === 'audit' && (
            <div className="min-h-[200px] flex-1 overflow-auto rounded-md border border-[var(--color-agentos-border)] bg-[var(--color-agentos-bg)] p-3 font-mono text-[11px] leading-relaxed text-[var(--color-agentos-muted)]">
              {(data?.events ?? []).map((ev, i) => (
                <div key={i} className="mb-1 border-b border-[var(--color-agentos-border)]/40 pb-1">
                  {JSON.stringify(ev)}
                </div>
              ))}
            </div>
          )}
          {panel === 'mri' && (
            <div className="min-h-[200px] flex-1">
              {!diagnosis && (
                <p className="text-sm text-[var(--color-agentos-muted)]">
                  Click &quot;System MRI&quot; above to generate a diagnostic report.
                </p>
              )}
              {diagnosis && (
                <pre className="max-h-[min(60vh,480px)] overflow-auto rounded-md border border-[var(--color-agentos-border)] bg-[var(--color-agentos-bg)] p-3 font-mono text-[11px] leading-relaxed text-[var(--color-agentos-fg)]">
                  {JSON.stringify(diagnosis, null, 2)}
                </pre>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
