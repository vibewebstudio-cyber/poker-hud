import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import StatCard from '../components/StatCard.jsx'
import FilterPanel from '../components/FilterPanel.jsx'
import ProfitGraph from '../components/ProfitGraph.jsx'
import { fetchFilterOptions, fetchHeroGraph, fetchHeroStats } from '../lib/api.js'

export default function DashboardPage() {
  const [options, setOptions] = useState(null)
  const [filters, setFilters] = useState({})
  const [stats, setStats] = useState(null)
  const [graph, setGraph] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchFilterOptions()
      .then(setOptions)
      .catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    setLoading(true)
    Promise.all([fetchHeroStats(filters), fetchHeroGraph(filters)])
      .then(([statsRes, graphRes]) => {
        setStats(statsRes)
        setGraph(graphRes)
        setError(null)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [filters])

  if (error) {
    return (
      <div className="max-w-3xl mx-auto mt-16 rounded-xl border border-rose-900 bg-rose-950/40 px-6 py-5 text-rose-300">
        <p className="font-medium">Couldn't reach the API.</p>
        <p className="text-sm text-rose-400 mt-1">
          {error} — make sure the backend is running (uvicorn api.routes:app --port 8001).
        </p>
      </div>
    )
  }

  if (!options || (loading && !stats)) {
    return <div className="max-w-6xl mx-auto mt-16 text-center text-slate-500">Loading…</div>
  }

  if (stats && stats.hands === 0) {
    return (
      <div className="max-w-3xl mx-auto mt-16 rounded-xl border border-slate-800 bg-slate-900/60 px-6 py-8 text-center">
        <p className="text-slate-300 font-medium">No hands imported yet.</p>
        <p className="text-sm text-slate-500 mt-2">
          <Link to="/import" className="text-cyan-400 hover:underline">
            Upload a hand history file
          </Link>{' '}
          to get started, or run{' '}
          <code className="text-slate-300">python cli.py import &lt;path&gt;</code> locally.
        </p>
      </div>
    )
  }

  const unitLabel =
    graph.series.length === 0
      ? ''
      : graph.mixed_formats
        ? 'mixed units — filter by format'
        : graph.series[0].format === 'cash'
          ? '$'
          : 'tournament chips'

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col gap-6">
      <header>
        <h1 className="text-xl font-semibold text-slate-100">Hero Dashboard</h1>
        <p className="text-sm text-slate-500">
          Stats and results computed from your imported hand histories.
        </p>
      </header>

      <FilterPanel options={options} filters={filters} onChange={setFilters} />

      {graph.mixed_formats && (
        <div className="rounded-xl border border-amber-900 bg-amber-950/30 px-4 py-3 text-sm text-amber-300">
          This range mixes cash-game results ($) with tournament results (chips) — the cumulative
          graph below isn't meaningful until you filter by Format.
        </div>
      )}

      <div className="flex flex-wrap gap-4">
        <StatCard label="Hands" value={stats.hands} />
        <StatCard label="VPIP" value={`${stats.vpip_pct}%`} />
        <StatCard label="PFR" value={`${stats.pfr_pct}%`} />
        <StatCard
          label="3-Bet"
          value={`${stats.three_bet_pct}%`}
          sublabel={`${stats.three_bet_opportunities} opportunities`}
        />
        <StatCard
          label="Net Result"
          value={graph.mixed_formats ? 'mixed' : stats.total_result}
          sublabel={graph.mixed_formats ? '$ and chips combined — filter by format' : undefined}
          tone={
            graph.mixed_formats
              ? 'neutral'
              : stats.total_result > 0
                ? 'positive'
                : stats.total_result < 0
                  ? 'negative'
                  : 'neutral'
          }
        />
        {!graph.mixed_formats && stats.bb_per_100 !== null && stats.bb_per_100 !== undefined && (
          <StatCard
            label="bb/100"
            value={stats.bb_per_100}
            tone={stats.bb_per_100 > 0 ? 'positive' : stats.bb_per_100 < 0 ? 'negative' : 'neutral'}
          />
        )}
      </div>

      <ProfitGraph series={graph.series} unitLabel={unitLabel} />
    </div>
  )
}
