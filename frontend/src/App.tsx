import { useState } from 'react'
import Dashboard from './components/Dashboard'
import TransactionTable from './components/TransactionTable'
import BudgetsAndGoals from './components/BudgetsAndGoals'
import Insights from './components/Insights'
import FinanceChat from './components/FinanceChat'
import WhatIf from './components/WhatIf'
import LearnAssistant from './components/LearnAssistant'
import Badge, { BADGES, type BadgeKind } from './components/Badge'

type Tab = 'dashboard' | 'transactions' | 'budgets' | 'insights' | 'chat' | 'whatif' | 'learn'

function App() {
  const [tab, setTab] = useState<Tab>('dashboard')

  const tabs: { id: Tab; label: string }[] = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'transactions', label: 'Transactions' },
    { id: 'budgets', label: 'Budgets & Goals' },
    { id: 'insights', label: 'Insights' },
    { id: 'chat', label: 'Ask FinSight' },
    { id: 'whatif', label: 'What-If' },
    { id: 'learn', label: 'Learn' },
  ]

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="bg-white border-b border-slate-100 px-6 py-3 flex items-center gap-6">
        <span className="font-semibold text-slate-800">FinSight</span>
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`text-sm px-3 py-1.5 rounded-md transition ${
              tab === t.id ? 'bg-slate-800 text-white' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="bg-white border-b border-slate-100 px-6 py-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400">
        <span>Legend:</span>
        {(Object.keys(BADGES) as BadgeKind[]).map((k) => (
          <span key={k} className="flex items-center gap-1.5">
            <Badge kind={k} small /> {BADGES[k].meaning}
          </span>
        ))}
      </div>

      {tab === 'dashboard' && <Dashboard />}
      {tab === 'transactions' && <TransactionTable />}
      {tab === 'budgets' && <BudgetsAndGoals />}
      {tab === 'insights' && <Insights />}
      {tab === 'chat' && <FinanceChat />}
      {tab === 'whatif' && <WhatIf />}
      {tab === 'learn' && <LearnAssistant />}
    </div>
  )
}

export default App
