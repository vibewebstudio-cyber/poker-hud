import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ReplayControls from '../components/ReplayControls.jsx'
import ReplayTable from '../components/ReplayTable.jsx'
import { fetchHandReplay } from '../lib/api.js'
import { describeAction, formatMoney } from '../lib/format.js'

const PLAY_INTERVAL_MS = 900

export default function ReplayerPage() {
  const { handId } = useParams()
  const [replay, setReplay] = useState(null)
  const [error, setError] = useState(null)
  const [stepIndex, setStepIndex] = useState(-1)
  const [isPlaying, setIsPlaying] = useState(false)
  const intervalRef = useRef(null)

  useEffect(() => {
    setReplay(null)
    setError(null)
    setStepIndex(-1)
    setIsPlaying(false)
    fetchHandReplay(handId)
      .then(setReplay)
      .catch((e) => setError(e.message))
  }, [handId])

  useEffect(() => {
    if (!isPlaying || !replay) return
    intervalRef.current = setInterval(() => {
      setStepIndex((i) => {
        if (i >= replay.steps.length - 1) {
          setIsPlaying(false)
          return i
        }
        return i + 1
      })
    }, PLAY_INTERVAL_MS)
    return () => clearInterval(intervalRef.current)
  }, [isPlaying, replay])

  const startingStacks = useMemo(() => {
    if (!replay) return {}
    return Object.fromEntries(replay.seats.map((s) => [s.name, s.starting_stack]))
  }, [replay])

  const foldedPlayers = useMemo(() => {
    if (!replay) return new Set()
    const folded = new Set()
    for (let i = 0; i <= stepIndex; i++) {
      const step = replay.steps[i]
      if (step.action_type === 'folds') folded.add(step.player)
    }
    return folded
  }, [replay, stepIndex])

  if (error) {
    return (
      <div className="max-w-3xl mx-auto mt-16 rounded-xl border border-rose-900 bg-rose-950/40 px-6 py-5 text-rose-300">
        <p className="font-medium">Couldn't load this hand.</p>
        <p className="text-sm text-rose-400 mt-1">{error}</p>
        <Link to="/hands" className="text-sm text-cyan-400 mt-3 inline-block">
          ← Back to hands
        </Link>
      </div>
    )
  }

  if (!replay) {
    return <div className="max-w-6xl mx-auto mt-16 text-center text-slate-500">Loading…</div>
  }

  const currentStep = stepIndex >= 0 ? replay.steps[stepIndex] : null
  const stacks = currentStep ? currentStep.stacks_after : startingStacks
  const pot = currentStep ? currentStep.pot_after : 0
  const board = currentStep ? currentStep.board : []
  const actingPlayer = currentStep ? currentStep.player : null

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 flex flex-col gap-6">
      <header className="flex items-center justify-between">
        <div>
          <Link to="/hands" className="text-sm text-slate-500 hover:text-slate-300">
            ← Back to hands
          </Link>
          <h1 className="text-xl font-semibold text-slate-100 mt-1">
            Hand #{replay.hand_number}
          </h1>
          <p className="text-sm text-slate-500">
            {replay.game_type} · {replay.stakes} · {replay.date?.slice(0, 16).replace('T', ' ')}
          </p>
        </div>
      </header>

      <ReplayTable
        replay={replay}
        currentStep={currentStep}
        foldedPlayers={foldedPlayers}
        stacks={stacks}
        pot={pot}
        board={board}
        actingPlayer={actingPlayer}
      />

      <ReplayControls
        stepIndex={stepIndex}
        totalSteps={replay.steps.length}
        isPlaying={isPlaying}
        onFirst={() => setStepIndex(-1)}
        onPrev={() => setStepIndex((i) => Math.max(-1, i - 1))}
        onNext={() => setStepIndex((i) => Math.min(replay.steps.length - 1, i + 1))}
        onLast={() => setStepIndex(replay.steps.length - 1)}
        onTogglePlay={() => setIsPlaying((p) => !p)}
      />

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-4 max-h-64 overflow-y-auto">
        <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-2">
          Action log
        </h2>
        <ol className="flex flex-col gap-1 text-sm">
          {replay.steps.map((step, i) => (
            <li
              key={i}
              className={`px-2 py-1 rounded cursor-pointer ${
                i === stepIndex
                  ? 'bg-cyan-900/50 text-cyan-200'
                  : i < stepIndex
                    ? 'text-slate-400'
                    : 'text-slate-600'
              }`}
              onClick={() => setStepIndex(i)}
            >
              <span className="text-xs uppercase text-slate-600 mr-2">{step.street}</span>
              <span className="font-medium">{step.player}</span>{' '}
              {describeAction(step, replay.format, replay.currency)}
            </li>
          ))}
        </ol>
      </div>

      <div className="text-sm text-slate-500">
        Final pot: {formatMoney(replay.pot_size, replay.format, replay.currency)}
      </div>
    </div>
  )
}
