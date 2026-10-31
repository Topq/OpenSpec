import { useState } from 'react'
import type { FundState } from './types'
import FundPanel from './components/FundPanel'
import DebugConsole from './components/DebugConsole'

const initialState: FundState = {
  phase: 'SELLING',
  purchased: false,
  currentProgress: 0,
  freeClaimed: [],
  payClaimed: [],
}

export default function App() {
  const [state, setState] = useState<FundState>(initialState)

  function handlePurchase() {
    if (state.purchased || state.phase !== 'SELLING') return
    setState(prev => ({ ...prev, purchased: true }))
  }

  function handleClaimFree(tierId: number) {
    setState(prev => (prev.freeClaimed.includes(tierId) ? prev : { ...prev, freeClaimed: [...prev.freeClaimed, tierId] }))
  }

  function handleClaimPay(tierId: number) {
    setState(prev => {
      if (!prev.purchased || prev.payClaimed.includes(tierId)) return prev
      return { ...prev, payClaimed: [...prev.payClaimed, tierId] }
    })
  }

  return (
    <div id="app-root" data-lr-component="surface.panel" style={{ width: '100%', height: '100%' }}>
      <FundPanel
        state={state}
        onPurchase={handlePurchase}
        onClaimFree={handleClaimFree}
        onClaimPay={handleClaimPay}
      />
      <DebugConsole state={state} setState={setState} />
    </div>
  )
}
