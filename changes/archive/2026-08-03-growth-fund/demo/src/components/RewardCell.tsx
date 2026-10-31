import type { CellClaimState, RewardItem } from '../types'

interface RewardCellProps {
  columnKey: 'free' | 'pay'
  tierId: number
  reward: RewardItem
  state: CellClaimState
  onClaim: () => void
}

export default function RewardCell({ columnKey, tierId, reward, state, onClaim }: RewardCellProps) {
  const locked = state === 'locked' || state === 'locked-by-purchase'
  const claimable = state === 'claimable'
  const claimed = state === 'claimed'

  return (
    <div
      id={`cell-${columnKey}-${tierId}`}
      data-lr-template="template.reward-cell"
      data-lr-bind={`tier-${tierId}-${columnKey}`}
      className={`reward-cell ${locked ? 'is-locked' : ''} ${claimed ? 'is-claimed' : ''}`}
    >
      <button
        id={`icon-${columnKey}-${tierId}`}
        data-lr-component="slot.item-icon"
        data-lr-action={`claim-${columnKey}`}
        className={`reward-icon ${claimable ? 'reward-icon--claimable' : ''}`}
        disabled={!claimable}
        onClick={claimable ? onClaim : undefined}
        style={{ cursor: claimable ? 'pointer' : 'default' }}
      >
        <span className="reward-icon-glyph">{reward.icon}</span>
        {locked && <span className="lock-badge">🔒</span>}
        {claimable && <span id={`redpoint-${columnKey}-${tierId}`} data-lr-component="feedback.red-point" className="red-point" />}
      </button>
      <div className="reward-count">x{reward.count}</div>
    </div>
  )
}
