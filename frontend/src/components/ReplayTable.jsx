import { formatMoney } from '../lib/format.js'

const CARD_SUIT_COLOR = { h: 'text-rose-400', d: 'text-rose-400', c: 'text-slate-200', s: 'text-slate-200' }

function Card({ code }) {
  if (!code) {
    return <div className="w-8 h-11 rounded border border-slate-600 bg-slate-800/50" />
  }
  const rank = code.slice(0, -1)
  const suit = code.slice(-1)
  const suitChar = { h: '♥', d: '♦', c: '♣', s: '♠' }[suit] || suit
  return (
    <div className="w-8 h-11 rounded bg-slate-50 border border-slate-300 flex flex-col items-center justify-center leading-none shadow">
      <span className={`text-sm font-bold ${CARD_SUIT_COLOR[suit] || 'text-slate-900'}`}>{rank}</span>
      <span className={`text-sm ${CARD_SUIT_COLOR[suit] || 'text-slate-900'}`}>{suitChar}</span>
    </div>
  )
}

function seatPosition(index, count) {
  const angle = (index / count) * 2 * Math.PI - Math.PI / 2
  const x = 50 + 44 * Math.cos(angle)
  const y = 50 + 40 * Math.sin(angle)
  return { left: `${x}%`, top: `${y}%` }
}

export default function ReplayTable({ replay, currentStep, foldedPlayers, stacks, pot, board, actingPlayer }) {
  const { seats, format, currency, hero_name: heroName, hero_cards: heroCards } = replay

  return (
    <div className="relative w-full aspect-[16/9] rounded-[40%] bg-gradient-to-b from-emerald-900 to-emerald-950 border-8 border-slate-800 shadow-xl">
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-2">
        <div className="flex gap-1">
          {[0, 1, 2, 3, 4].map((i) => (
            <Card key={i} code={board[i]} />
          ))}
        </div>
        <div className="text-emerald-200 text-sm font-medium bg-black/30 rounded-full px-3 py-1">
          Pot: {formatMoney(pot, format, currency)}
        </div>
      </div>

      {seats.map((seat, i) => {
        const pos = seatPosition(i, seats.length)
        const folded = foldedPlayers.has(seat.name)
        const isActing = actingPlayer === seat.name
        const stack = stacks[seat.name]
        const isHero = seat.name === heroName
        const cards = isHero ? heroCards?.split(' ') : seat.shown_cards?.split(' ')

        return (
          <div
            key={seat.seat}
            className="absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-1"
            style={pos}
          >
            <div className="flex gap-0.5">
              {cards ? (
                cards.map((c, idx) => <Card key={idx} code={c} />)
              ) : (
                <>
                  <Card />
                  <Card />
                </>
              )}
            </div>
            <div
              className={`rounded-lg px-3 py-1.5 text-center min-w-[110px] border transition-colors ${
                isActing
                  ? 'bg-cyan-900/80 border-cyan-400'
                  : folded
                    ? 'bg-slate-900/60 border-slate-800 opacity-50'
                    : 'bg-slate-900/80 border-slate-700'
              }`}
            >
              <div className="text-xs font-semibold text-slate-100 truncate max-w-[100px]">
                {seat.name} {seat.position && <span className="text-slate-500">({seat.position})</span>}
              </div>
              <div className="text-xs text-slate-400 tabular-nums">
                {formatMoney(stack, format, currency)}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
