export function formatMoney(amount, format, currency) {
  if (amount === null || amount === undefined) return ''
  const rounded = Math.round(amount * 100) / 100
  if (format === 'cash') {
    return `${currency || '$'}${rounded.toFixed(2)}`
  }
  return `${rounded.toLocaleString()}`
}

export function describeAction(step, format, currency) {
  const m = (amt) => formatMoney(amt, format, currency)
  switch (step.action_type) {
    case 'posts_sb':
      return `posts small blind ${m(step.amount)}`
    case 'posts_bb':
      return `posts big blind ${m(step.amount)}`
    case 'posts_ante':
      return `posts ante ${m(step.amount)}`
    case 'folds':
      return 'folds'
    case 'checks':
      return 'checks'
    case 'calls':
      return `calls ${m(step.amount)}`
    case 'bets':
      return `bets ${m(step.amount)}`
    case 'raises':
      return `raises to ${m(step.amount)}`
    case 'uncalled_return':
      return `uncalled bet ${m(step.amount)} returned`
    case 'collected':
      return `collected ${m(step.amount)} from pot`
    default:
      return step.action_type
  }
}
