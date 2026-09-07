export default function ReplayControls({
  stepIndex,
  totalSteps,
  isPlaying,
  onFirst,
  onPrev,
  onNext,
  onLast,
  onTogglePlay,
}) {
  const atStart = stepIndex < 0
  const atEnd = stepIndex >= totalSteps - 1

  return (
    <div className="flex items-center justify-center gap-2">
      <ControlButton label="⏮" title="Jump to start" onClick={onFirst} disabled={atStart} />
      <ControlButton label="◀" title="Previous action" onClick={onPrev} disabled={atStart} />
      <ControlButton
        label={isPlaying ? '⏸' : '▶'}
        title={isPlaying ? 'Pause' : 'Play'}
        onClick={onTogglePlay}
        disabled={atEnd && !isPlaying}
        wide
      />
      <ControlButton label="▶" title="Next action" onClick={onNext} disabled={atEnd} />
      <ControlButton label="⏭" title="Jump to end" onClick={onLast} disabled={atEnd} />
      <span className="ml-3 text-sm text-slate-500 tabular-nums">
        {stepIndex + 1} / {totalSteps}
      </span>
    </div>
  )
}

function ControlButton({ label, title, onClick, disabled, wide }) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      disabled={disabled}
      className={`${wide ? 'px-4' : 'px-3'} py-2 rounded-lg border border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-slate-800 transition-colors`}
    >
      {label}
    </button>
  )
}
