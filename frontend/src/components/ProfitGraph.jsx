import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function ProfitGraph({ series, unitLabel }) {
  const data = series.map((point, i) => ({
    index: i + 1,
    cumulative: point.cumulative,
    date: point.date,
  }))

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-4">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-sm font-medium uppercase tracking-wide text-slate-500">
          Cumulative result
        </h2>
        <span className="text-xs text-slate-500">{unitLabel}</span>
      </div>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="index"
              stroke="#64748b"
              fontSize={12}
              tickFormatter={(v) => `#${v}`}
            />
            <YAxis stroke="#64748b" fontSize={12} />
            <Tooltip
              contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
              labelStyle={{ color: '#94a3b8' }}
              formatter={(value) => [value, unitLabel]}
              labelFormatter={(v, payload) => payload?.[0]?.payload?.date?.slice(0, 10) ?? `Hand #${v}`}
            />
            <Line
              type="monotone"
              dataKey="cumulative"
              stroke="#22d3ee"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
