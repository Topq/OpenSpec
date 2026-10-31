export type ConditionType = 'LEVEL' | 'TOWER_FLOOR' | 'CUMULATIVE_LOGIN' | 'QUEST' | 'POWER'

export interface RewardItem {
  itemId: string
  itemName: string
  icon: string
  count: number
}

export interface RewardTier {
  id: number
  conditionType: ConditionType
  conditionValue: number
  freeReward: RewardItem
  payReward: RewardItem
}

export interface FundInfo {
  activeId: number
  rechargeId: number
  name: string
  price: string
  tiers: RewardTier[]
}

export type FundPhase = 'SELLING' | 'ENDED'

export interface FundState {
  phase: FundPhase
  purchased: boolean
  currentProgress: number
  freeClaimed: number[]
  payClaimed: number[]
}

export type CellClaimState = 'locked' | 'claimable' | 'claimed' | 'locked-by-purchase'
