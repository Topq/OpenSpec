import type { FundInfo } from './types'

export const FUND_INFO: FundInfo = {
  activeId: 10008,
  rechargeId: 1013,
  name: '成长计划',
  price: '¥30',
  tiers: [
    { id: 1, conditionType: 'LEVEL', conditionValue: 20, freeReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 188 }, payReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 1080 } },
    { id: 2, conditionType: 'LEVEL', conditionValue: 25, freeReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 188 }, payReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 1080 } },
    { id: 3, conditionType: 'LEVEL', conditionValue: 30, freeReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 188 }, payReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 1080 } },
    { id: 4, conditionType: 'LEVEL', conditionValue: 35, freeReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 188 }, payReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 1080 } },
    { id: 5, conditionType: 'LEVEL', conditionValue: 40, freeReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 188 }, payReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 1080 } },
    { id: 6, conditionType: 'LEVEL', conditionValue: 45, freeReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 188 }, payReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 1080 } },
    { id: 7, conditionType: 'LEVEL', conditionValue: 50, freeReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 188 }, payReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 1080 } },
    { id: 8, conditionType: 'LEVEL', conditionValue: 55, freeReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 188 }, payReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 1080 } },
    { id: 9, conditionType: 'LEVEL', conditionValue: 60, freeReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 188 }, payReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 1080 } },
    { id: 10, conditionType: 'LEVEL', conditionValue: 65, freeReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 188 }, payReward: { itemId: '1003', itemName: '紫晶', icon: '💎', count: 1080 } },
  ],
}

export const CONDITION_LABEL: Record<string, string> = {
  LEVEL: 'Lv.',
  TOWER_FLOOR: '爬塔',
  CUMULATIVE_LOGIN: '登录',
  QUEST: '任务',
  POWER: '战力',
}

export function conditionText(conditionType: string, conditionValue: number): string {
  const label = CONDITION_LABEL[conditionType] ?? conditionType
  return `${label}${conditionValue}`
}
