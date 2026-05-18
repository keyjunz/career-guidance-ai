import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import {
  fetchCostLogSummary,
  fetchCostLogs,
  type AdminCostLog,
  type UserCostSummary,
} from '../../services/adminApi'
import { clearAuthTokens, getAccessToken } from '../../services/authStorage'
import { getMe } from '../../services/authApi'

function formatTokens(n: number): string {
  return n.toLocaleString()
}

export function AdminCostLogsPage() {
  const navigate = useNavigate()
  const [logs, setLogs] = useState<AdminCostLog[]>([])
  const [summary, setSummary] = useState<UserCostSummary[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [logRows, summaryRows] = await Promise.all([
        fetchCostLogs(100, 0),
        fetchCostLogSummary(),
      ])
      setLogs(logRows)
      setSummary(summaryRows)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cost logs.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let mounted = true
    async function init() {
      const token = getAccessToken()
      if (!token) {
        navigate('/login', { replace: true })
        return
      }
      try {
        const user = await getMe()
        if (user.role !== 'admin') {
          navigate('/chat', { replace: true })
          return
        }
        if (mounted) await load()
      } catch {
        clearAuthTokens()
        navigate('/login', { replace: true })
      }
    }
    init()
    return () => {
      mounted = false
    }
  }, [load, navigate])

  return (
    <div className="h-screen overflow-y-auto bg-background px-4 py-8 text-on-surface sm:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Token usage</h1>
            <p className="mt-1 text-sm text-on-surface/65">
              Per-turn cost logs linked to chat messages.
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              to="/chat"
              className="u-focus rounded-xl border border-outline-variant/25 bg-surface-container-highest px-4 py-2 text-sm font-semibold text-on-surface shadow-sm transition-colors hover:bg-surface-container-high"
            >
              Back to chat
            </Link>
            <button
              type="button"
              onClick={() => load()}
              className="u-focus rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary/90"
            >
              Refresh
            </button>
          </div>
        </div>

        {error ? (
          <p className="u-alert u-alert-error mb-4 px-4 py-3 text-sm">{error}</p>
        ) : null}

        {loading ? (
          <p className="text-sm text-on-surface/60">Loading…</p>
        ) : (
          <>
            <section className="u-card mb-8 overflow-hidden">
              <h2 className="border-b border-on-surface/8 px-4 py-3 text-sm font-semibold uppercase tracking-wide text-on-surface/55">
                By user
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[480px] text-left text-sm">
                  <thead className="bg-surface-container-low/80 text-on-surface/55">
                    <tr>
                      <th className="px-4 py-2 font-medium">User</th>
                      <th className="px-4 py-2 font-medium">Input</th>
                      <th className="px-4 py-2 font-medium">Output</th>
                      <th className="px-4 py-2 font-medium">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.map((row) => (
                      <tr key={row.user_id} className="border-t border-on-surface/6">
                        <td className="px-4 py-2.5">
                          {row.user_name ?? row.user_id.slice(0, 8)}
                        </td>
                        <td className="px-4 py-2.5 tabular-nums">
                          {formatTokens(row.input_tokens)}
                        </td>
                        <td className="px-4 py-2.5 tabular-nums">
                          {formatTokens(row.output_tokens)}
                        </td>
                        <td className="px-4 py-2.5 font-medium tabular-nums">
                          {formatTokens(row.total_tokens)}
                        </td>
                      </tr>
                    ))}
                    {summary.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-4 py-6 text-on-surface/50">
                          No usage recorded yet.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="u-card overflow-hidden">
              <h2 className="border-b border-on-surface/8 px-4 py-3 text-sm font-semibold uppercase tracking-wide text-on-surface/55">
                Recent turns
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead className="bg-surface-container-low/80 text-on-surface/55">
                    <tr>
                      <th className="px-4 py-2 font-medium">Time</th>
                      <th className="px-4 py-2 font-medium">User</th>
                      <th className="px-4 py-2 font-medium">Type</th>
                      <th className="px-4 py-2 font-medium">Model</th>
                      <th className="px-4 py-2 font-medium">In</th>
                      <th className="px-4 py-2 font-medium">Out</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((row) => (
                      <tr key={row.id} className="border-t border-on-surface/6">
                        <td className="whitespace-nowrap px-4 py-2.5 text-on-surface/70">
                          {row.timestamp
                            ? new Date(row.timestamp).toLocaleString()
                            : '—'}
                        </td>
                        <td className="px-4 py-2.5">
                          {row.user_name ?? row.user_id.slice(0, 8)}
                        </td>
                        <td className="px-4 py-2.5">{row.request_type}</td>
                        <td className="px-4 py-2.5 text-on-surface/75">{row.model_name}</td>
                        <td className="px-4 py-2.5 tabular-nums">
                          {formatTokens(row.input_tokens)}
                        </td>
                        <td className="px-4 py-2.5 tabular-nums">
                          {formatTokens(row.output_tokens)}
                        </td>
                      </tr>
                    ))}
                    {logs.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-6 text-on-surface/50">
                          No cost log rows yet. Send a chat message to create one.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  )
}
