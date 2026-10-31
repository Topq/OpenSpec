import type { CellClaimState, FundState } from '../types'
import { FUND_INFO } from '../data'
import RewardRow from './RewardRow'

interface FundPanelProps {
  state: FundState
  onPurchase: () => void
  onClaimFree: (tierId: number) => void
  onClaimPay: (tierId: number) => void
}

export default function FundPanel({ state, onPurchase, onClaimFree, onClaimPay }: FundPanelProps) {
  const selling = state.phase === 'SELLING'
  const allFreeClaimed = state.freeClaimed.length === FUND_INFO.tiers.length
  const allPayClaimed = state.payClaimed.length === FUND_INFO.tiers.length
  const allDone = allFreeClaimed && (state.purchased ? allPayClaimed : true)

  function freeState(tierId: number, conditionValue: number): CellClaimState {
    if (state.freeClaimed.includes(tierId)) return 'claimed'
    if (state.currentProgress >= conditionValue) return 'claimable'
    return 'locked'
  }

  function payState(tierId: number, conditionValue: number): CellClaimState {
    if (!state.purchased) return 'locked-by-purchase'
    if (state.payClaimed.includes(tierId)) return 'claimed'
    if (state.currentProgress >= conditionValue) return 'claimable'
    return 'locked'
  }

  return (
    <div id="panel-growth-fund" data-lr-component="surface.page" className="fund-panel">
      <div id="panel-header" className="fund-header">
        <div className="fund-header-info">
          <div id="text-fund-name" data-lr-component="text.localized" className="fund-name">{FUND_INFO.name}</div>
          <div id="text-fund-price" data-lr-component="text.localized" className="fund-price">{FUND_INFO.price}</div>
        </div>

        {!selling && (
          <div id="tag-ended" className="phase-tag phase-tag--ended">售卖已结束</div>
        )}

        <button
          id="btn-purchase"
          data-lr-component="control.button"
          data-lr-action="purchase-fund"
          className={`purchase-button ${state.purchased ? 'purchase-button--done' : ''} ${!selling ? 'purchase-button--disabled' : ''}`}
          disabled={state.purchased || !selling}
          onClick={onPurchase}
        >
          {state.purchased ? '已购买' : '购买'}
        </button>
      </div>

      <div id="list-reward-tiers" data-lr-component="list.scroll" className="reward-list">
        <div className="reward-list-head">
          <div className="condition-col">条件进度</div>
          <div className="reward-cell-head">免费奖励</div>
          <div className="reward-cell-head">投资奖励</div>
        </div>

        <div className="reward-list-body">
          {FUND_INFO.tiers.map(tier => (
            <RewardRow
              key={tier.id}
              tier={tier}
              currentProgress={state.currentProgress}
              freeState={freeState(tier.id, tier.conditionValue)}
              payState={payState(tier.id, tier.conditionValue)}
              onClaimFree={() => onClaimFree(tier.id)}
              onClaimPay={() => onClaimPay(tier.id)}
            />
          ))}
        </div>
      </div>

      {allDone && (
        <div id="tag-completed" className="completed-badge">已完成</div>
      )}
    </div>
  )
}
