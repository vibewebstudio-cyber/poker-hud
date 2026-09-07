export default function StatCard({ label, value, sublabel, tone = 'neutral' }) {
  const toneClass = {
    neutral: 'text-slate-100',
    positive: 'text-emerald-400',
    negative: 'text-rose-400',
  }[tone]

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-4 flex flex-col gap-1 min-w-[140px]">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</span>
      <span className={`text-2xl font-semibold tabular-nums ${toneClass}`}>{value}</span>
      {sublabel && <span className="text-xs text-slate-500">{sublabel}</span>}
    </div>
  )
}
