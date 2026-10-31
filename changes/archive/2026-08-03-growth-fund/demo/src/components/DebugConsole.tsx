import { useState, type CSSProperties } from 'react'
import type { FundState } from '../types'
import { FUND_INFO } from '../data'

interface DebugConsoleProps {
  state: FundState
  setState: (updater: (prev: FundState) => FundState) => void
}

export default function DebugConsole({ state, setState }: DebugConsoleProps) {
  const [open, setOpen] = useState(true)

  function addLevel(delta: number) {
    setState(prev => ({ ...prev, currentProgress: Math.max(0, prev.currentProgress + delta) }))
  }

  function jumpToTier(tierId: number) {
    const tier = FUND_INFO.tiers.find(t => t.id === tierId)
    if (!tier) return
    setState(prev => ({ ...prev, currentProgress: tier.conditionValue }))
  }

  function togglePurchase() {
    setState(prev => ({ ...prev, purchased: !prev.purchased }))
  }

  function togglePhase() {
    setState(prev => ({ ...prev, phase: prev.phase === 'SELLING' ? 'ENDED' : 'SELLING' }))
  }

  function resetAll() {
    setState(() => ({ phase: 'SELLING', purchased: false, currentProgress: 0, freeClaimed: [], payClaimed: [] }))
  }

  function claimAllFree() {
    setState(prev => {
      const claimable = FUND_INFO.tiers.filter(t => prev.currentProgress >= t.conditionValue).map(t => t.id)
      return { ...prev, freeClaimed: Array.from(new Set([...prev.freeClaimed, ...claimable])) }
    })
  }

  function claimAllPay() {
    setState(prev => {
      if (!prev.purchased) return prev
      const claimable = FUND_INFO.tiers.filter(t => prev.currentProgress >= t.conditionValue).map(t => t.id)
      return { ...prev, payClaimed: Array.from(new Set([...prev.payClaimed, ...claimable])) }
    })
  }

  return (
    <div style={{ position: 'fixed', bottom: 16, right: 16, zIndex: 9999, fontFamily: 'sans-serif' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{ padding: '6px 12px', borderRadius: 6, border: 'none', background: '#333', color: '#fff', cursor: 'pointer' }}
      >
        {open ? '收起调试' : '调试面板'}
      </button>

      {open && (
        <div style={{ marginTop: 8, padding: 12, background: 'rgba(0,0,0,0.85)', color: '#fff', borderRadius: 8, width: 260, fontSize: 12 }}>
          <div style={{ marginBottom: 8 }}>
            <strong>条件进度</strong>：{state.currentProgress}
            <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
              <button onClick={() => addLevel(5)} style={debugBtn}>Lv +5</button>
              <button onClick={() => addLevel(-5)} style={debugBtn}>Lv -5</button>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
              {FUND_INFO.tiers.map(t => (
                <button key={t.id} onClick={() => jumpToTier(t.id)} style={debugBtnSmall}>跳到档{t.id}</button>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: 8 }}>
            <strong>购买态</strong>：{state.purchased ? '已购买' : '未购买'}
            <div style={{ marginTop: 6 }}>
              <button onClick={togglePurchase} style={debugBtn}>切换购买态</button>
            </div>
          </div>

          <div style={{ marginBottom: 8 }}>
            <strong>售卖阶段</strong>：{state.phase === 'SELLING' ? '售卖中' : '已结束'}
            <div style={{ marginTop: 6 }}>
              <button onClick={togglePhase} style={debugBtn}>切换售卖阶段</button>
            </div>
          </div>

          <div style={{ marginBottom: 8 }}>
            <strong>领取</strong>
            <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
              <button onClick={claimAllFree} style={debugBtn}>一键领可领免费</button>
              <button onClick={claimAllPay} style={debugBtn}>一键领可领投资</button>
            </div>
          </div>

          <button onClick={resetAll} style={{ ...debugBtn, background: '#a33', width: '100%' }}>重置全部</button>
        </div>
      )}
    </div>
  )
}

const debugBtn: CSSProperties = {
  padding: '4px 8px',
  borderRadius: 4,
  border: '1px solid #555',
  background: '#222',
  color: '#fff',
  cursor: 'pointer',
  fontSize: 12,
}

const debugBtnSmall: CSSProperties = {
  ...debugBtn,
  padding: '2px 6px',
  fontSize: 11,
}
