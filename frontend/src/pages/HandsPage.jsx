import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import FilterPanel from '../components/FilterPanel.jsx'
import { fetchFilterOptions, fetchHands } from '../lib/api.js'
import { formatMoney } from '../lib/format.js'

export default function HandsPage() {
  const [options, setOptions] = useState(null)
  const [filters, setFilters] = useState({})
  const [hands, setHands] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchFilterOptions().then(setOptions).catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    fetchHands(filters)
      .then((res) => setHands(res.hands))
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

  if (!options || !hands) {
    return <div className="max-w-6xl mx-auto mt-16 text-center text-slate-500">Loading…</div>
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col gap-6">
      <header>
        <h1 className="text-xl font-semibold text-slate-100">Hands</h1>
        <p className="text-sm text-slate-500">Click a hand to replay it action-by-action.</p>
      </header>

      <FilterPanel options={options} filters={filters} onChange={setFilters} />

      {hands.length === 0 ? (
        <p className="text-slate-500 text-sm">No hands match these filters.</p>
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500 border-b border-slate-800">
                <th className="px-4 py-2 font-medium">Date</th>
                <th className="px-4 py-2 font-medium">Format</th>
                <th className="px-4 py-2 font-medium">Stakes</th>
                <th className="px-4 py-2 font-medium">Pos</th>
                <th className="px-4 py-2 font-medium">Cards</th>
                <th className="px-4 py-2 font-medium">Board</th>
                <th className="px-4 py-2 font-medium text-right">Result</th>
              </tr>
            </thead>
            <tbody>
              {hands.map((h) => (
                <tr key={h.hand_id} className="border-b border-slate-800/60 last:border-0">
                  <td className="px-4 py-2">
                    <Link
                      to={`/hands/${h.hand_id}`}
                      className="text-slate-300 hover:text-cyan-400"
                    >
                      {h.date?.slice(0, 16).replace('T', ' ')}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-400 capitalize">{h.format}</td>
                  <td className="px-4 py-2 text-slate-400">{h.stakes}</td>
                  <td className="px-4 py-2 text-slate-400">{h.position || '—'}</td>
                  <td className="px-4 py-2 text-slate-300 tabular-nums">{h.hero_cards || '—'}</td>
                  <td className="px-4 py-2 text-slate-500 tabular-nums">
                    {h.board.length ? h.board.join(' ') : '—'}
                  </td>
                  <td
                    className={`px-4 py-2 text-right tabular-nums ${
                      h.hero_result > 0
                        ? 'text-emerald-400'
                        : h.hero_result < 0
                          ? 'text-rose-400'
                          : 'text-slate-400'
                    }`}
                  >
                    {formatMoney(h.hero_result, h.format, '$')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
