import type { CellClaimState, RewardTier } from '../types'
import { conditionText } from '../data'
import RewardCell from './RewardCell'

interface RewardRowProps {
  tier: RewardTier
  currentProgress: number
  freeState: CellClaimState
  payState: CellClaimState
  onClaimFree: () => void
  onClaimPay: () => void
}

export default function RewardRow({ tier, currentProgress, freeState, payState, onClaimFree, onClaimPay }: RewardRowProps) {
  const target = tier.conditionValue
  const progressText = `${conditionText(tier.conditionType, Math.min(currentProgress, target))}/${conditionText(tier.conditionType, target)}`

  return (
    <div id={`row-tier-${tier.id}`} data-lr-template="template.reward-cell" data-lr-slot="row" className="reward-row">
      <div id={`progress-${tier.id}`} data-lr-component="control.progress" className="condition-col">
        <span className="condition-text">{progressText}</span>
        <div className="condition-bar">
          <div className="condition-bar-fill" style={{ width: `${Math.min(100, (currentProgress / target) * 100)}%` }} />
        </div>
      </div>

      <RewardCell
        columnKey="free"
        tierId={tier.id}
        reward={tier.freeReward}
        state={freeState}
        onClaim={onClaimFree}
      />

      <RewardCell
        columnKey="pay"
        tierId={tier.id}
        reward={tier.payReward}
        state={payState}
        onClaim={onClaimPay}
      />
    </div>
  )
}
