export default function FilterPanel({ options, filters, onChange, showPosition = true }) {
  const update = (key) => (e) => {
    const value = e.target.value
    onChange({ ...filters, [key]: value || undefined })
  }

  return (
    <div className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-4">
      <Field label="From">
        <input
          type="date"
          value={filters.date_from ? filters.date_from.slice(0, 10) : ''}
          onChange={update('date_from')}
          className="bg-slate-800 border border-slate-700 rounded-md px-2 py-1 text-sm text-slate-100"
        />
      </Field>
      <Field label="To">
        <input
          type="date"
          value={filters.date_to ? filters.date_to.slice(0, 10) : ''}
          onChange={update('date_to')}
          className="bg-slate-800 border border-slate-700 rounded-md px-2 py-1 text-sm text-slate-100"
        />
      </Field>
      <Field label="Format">
        <select
          value={filters.format || ''}
          onChange={update('format')}
          className="bg-slate-800 border border-slate-700 rounded-md px-2 py-1 text-sm text-slate-100"
        >
          <option value="">All</option>
          {options.formats.map((f) => (
            <option key={f} value={f}>
              {f === 'cash' ? 'Cash' : 'Tournament'}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Stakes">
        <select
          value={filters.stakes || ''}
          onChange={update('stakes')}
          className="bg-slate-800 border border-slate-700 rounded-md px-2 py-1 text-sm text-slate-100"
        >
          <option value="">All</option>
          {options.stakes.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </Field>
      {showPosition && (
        <Field label="Position">
          <select
            value={filters.position || ''}
            onChange={update('position')}
            className="bg-slate-800 border border-slate-700 rounded-md px-2 py-1 text-sm text-slate-100"
          >
            <option value="">All</option>
            {options.positions.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </Field>
      )}
      {Object.values(filters).some(Boolean) && (
        <button
          onClick={() => onChange({})}
          className="text-sm text-slate-400 hover:text-slate-200 underline underline-offset-2"
        >
          Clear filters
        </button>
      )}
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</span>
      {children}
    </label>
  )
}
