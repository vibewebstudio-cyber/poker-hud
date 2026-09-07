import { useEffect, useState } from 'react'
import FilterPanel from '../components/FilterPanel.jsx'
import { fetchFilterOptions, fetchLeaks } from '../lib/api.js'

export default function LeaksPage() {
  const [options, setOptions] = useState(null)
  const [filters, setFilters] = useState({})
  const [flags, setFlags] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchFilterOptions().then(setOptions).catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    fetchLeaks(filters)
      .then((res) => setFlags(res.flags))
      .catch((e) => setError(e.message))
  }, [filters])

  if (error) {
    return (
      <div className="max-w-3xl mx-auto mt-16 rounded-xl border border-rose-900 bg-rose-950/40 px-6 py-5 text-rose-300">
        <p className="font-medium">Couldn't reach the API.</p>
        <p className="text-sm text-rose-400 mt-1">{error}</p>
      </div>
    )
  }

  if (!options || !flags) {
    return <div className="max-w-4xl mx-auto mt-16 text-center text-slate-500">Loading…</div>
  }

  const isInsufficientData = flags.length === 1 && flags[0].rule_id === 'insufficient_data'
  const sorted = [...flags].sort((a, b) => (a.severity === b.severity ? 0 : a.severity === 'warning' ? -1 : 1))

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 flex flex-col gap-6">
      <header>
        <h1 className="text-xl font-semibold text-slate-100">Leak Finder</h1>
        <p className="text-sm text-slate-500">
          Rule-of-thumb checks against typical preflop baselines — a starting point for what to
          look at, not a verdict.
        </p>
      </header>

      <FilterPanel options={options} filters={filters} onChange={setFilters} showPosition={false} />

      {isInsufficientData ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-6 py-8 text-center">
          <p className="text-slate-300 font-medium">{flags[0].title}</p>
          <p className="text-sm text-slate-500 mt-2">{flags[0].detail}</p>
        </div>
      ) : flags.length === 0 ? (
        <div className="rounded-xl border border-emerald-900 bg-emerald-950/30 px-6 py-8 text-center">
          <p className="text-emerald-300 font-medium">No leaks flagged in this range.</p>
          <p className="text-sm text-emerald-400/70 mt-2">
            Your stats are within the typical baselines this tool checks against.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {sorted.map((flag, i) => (
            <LeakCard key={i} flag={flag} />
          ))}
        </div>
      )}
    </div>
  )
}

function LeakCard({ flag }) {
  const isWarning = flag.severity === 'warning'
  return (
    <div
      className={`rounded-xl border px-5 py-4 ${
        isWarning ? 'border-amber-900 bg-amber-950/20' : 'border-slate-800 bg-slate-900/60'
      }`}
    >
      <div className="flex items-center gap-2 mb-1">
        <span
          className={`text-[10px] font-semibold uppercase tracking-wide rounded-full px-2 py-0.5 ${
            isWarning ? 'bg-amber-900/60 text-amber-300' : 'bg-slate-800 text-slate-400'
          }`}
        >
          {flag.severity}
        </span>
        <h2 className="text-sm font-semibold text-slate-100">{flag.title}</h2>
        {flag.position && (
          <span className="text-xs text-slate-500">({flag.position})</span>
        )}
      </div>
      <p className="text-sm text-slate-400">{flag.detail}</p>
    </div>
  )
}
