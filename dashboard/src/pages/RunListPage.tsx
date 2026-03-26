import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../lib/api'
import type { RunRow } from '../types/api'

function StatusBadge({ status }: { status: string | null | undefined }) {
  const s = status ?? 'unknown'
  const cls =
    s === 'completed'
      ? 'bg-emerald-500/15 text-emerald-300'
      : s === 'failed' || s === 'policy_blocked'
        ? 'bg-red-500/15 text-red-300'
        : s === 'pending_approval' || s === 'paused'
          ? 'bg-amber-500/15 text-amber-300'
          : s === 'running'
            ? 'bg-sky-500/15 text-sky-300'
            : 'bg-[var(--color-agentos-border)] text-[var(--color-agentos-muted)]'
  return (
    <span
      className={`inline-flex rounded px-2 py-0.5 font-mono text-xs ${cls}`}
    >
      {s}
    </span>
  )
}

/** Run list with GET /api/runs, filters, and new-run modal. */
export function RunListPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [runs, setRuns] = useState<RunRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [wfPath, setWfPath] = useState('workflows/sample.yaml')
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    setError(null)
    try {
      const r = await apiFetch('/api/runs')
      if (!r.ok) throw new Error(await r.text())
      const data = (await r.json()) as RunRow[]
      setRuns(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load runs')
      setRuns([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const t = window.setInterval(() => void load(), 3000)
    return () => window.clearInterval(t)
  }, [load])

  const filtered =
    statusFilter === 'all'
      ? runs
      : runs.filter((x) => (x.status ?? '') === statusFilter)

  async function createRun() {
    setCreating(true)
    setError(null)
    try {
      const r = await apiFetch('/api/runs', {
        method: 'POST',
        body: JSON.stringify({ workflow_path: wfPath }),
      })
      if (!r.ok) throw new Error(await r.text())
      const data = (await r.json()) as { run_id: string }
      setModalOpen(false)
      window.location.href = `/runs/${encodeURIComponent(data.run_id)}`
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-[var(--color-agentos-border)] bg-[var(--color-agentos-surface)]/80 px-8 py-6 backdrop-blur-sm">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Runs</h1>
            <p className="mt-1 text-sm text-[var(--color-agentos-muted)]">
              Workflows executed through AgentOS — refreshed every 3s.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="rounded-md bg-[var(--color-agentos-accent)] px-4 py-2 text-sm font-medium text-[var(--color-agentos-bg)] transition-opacity hover:opacity-90"
          >
            New run
          </button>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-3 border-b border-[var(--color-agentos-border)] bg-[var(--color-agentos-bg)] px-8 py-3">
        <label className="flex items-center gap-2 text-sm text-[var(--color-agentos-muted)]">
          Status
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded border border-[var(--color-agentos-border)] bg-[var(--color-agentos-elevated)] px-2 py-1.5 font-mono text-xs text-[var(--color-agentos-fg)]"
          >
            <option value="all">All</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="pending_approval">Pending approval</option>
            <option value="policy_blocked">Policy blocked</option>
            <option value="paused">Paused</option>
          </select>
        </label>
        {error && (
          <span className="text-sm text-red-400" role="alert">
            {error}
          </span>
        )}
      </div>

      <main className="flex-1 overflow-auto px-8 py-6">
        <div className="overflow-hidden rounded-lg border border-[var(--color-agentos-border)] bg-[var(--color-agentos-surface)]">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--color-agentos-border)] text-[var(--color-agentos-muted)]">
                <th className="px-4 py-3 font-medium">Run ID</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Workflow</th>
                <th className="px-4 py-3 font-medium">Started</th>
                <th className="px-4 py-3 font-medium">Steps</th>
                <th className="px-4 py-3 font-medium">Project</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-12 text-center font-mono text-sm text-[var(--color-agentos-muted)]"
                  >
                    Loading…
                  </td>
                </tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-12 text-center font-mono text-sm text-[var(--color-agentos-muted)]"
                  >
                    No runs match. Start the API and create a run.
                  </td>
                </tr>
              )}
              {!loading &&
                filtered.map((row) => (
                  <tr
                    key={row.run_id}
                    className="border-b border-[var(--color-agentos-border)]/60 hover:bg-[var(--color-agentos-elevated)]/40"
                  >
                    <td className="px-4 py-3 font-mono text-xs">
                      <Link
                        to={`/runs/${encodeURIComponent(row.run_id)}`}
                        className="text-[var(--color-agentos-accent)] hover:underline"
                      >
                        {row.run_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={row.status} />
                    </td>
                    <td className="px-4 py-3">{row.workflow_name ?? '—'}</td>
                    <td className="px-4 py-3 font-mono text-xs text-[var(--color-agentos-muted)]">
                      {row.started_at ?? '—'}
                    </td>
                    <td className="px-4 py-3">{row.step_count ?? '—'}</td>
                    <td className="px-4 py-3 text-[var(--color-agentos-muted)]">
                      {row.project ?? '—'}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </main>

      {modalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-md rounded-lg border border-[var(--color-agentos-border)] bg-[var(--color-agentos-surface)] p-6 shadow-xl">
            <h2 className="text-lg font-semibold">New run</h2>
            <p className="mt-1 text-sm text-[var(--color-agentos-muted)]">
              Path to workflow YAML on the AgentOS server filesystem.
            </p>
            <label className="mt-4 block text-sm">
              <span className="text-[var(--color-agentos-muted)]">Workflow path</span>
              <input
                value={wfPath}
                onChange={(e) => setWfPath(e.target.value)}
                className="mt-1 w-full rounded-md border border-[var(--color-agentos-border)] bg-[var(--color-agentos-bg)] px-3 py-2 font-mono text-sm"
              />
            </label>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="rounded-md border border-[var(--color-agentos-border)] px-4 py-2 text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={creating}
                onClick={() => void createRun()}
                className="rounded-md bg-[var(--color-agentos-accent)] px-4 py-2 text-sm font-medium text-[var(--color-agentos-bg)] disabled:opacity-50"
              >
                {creating ? 'Starting…' : 'Start run'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
