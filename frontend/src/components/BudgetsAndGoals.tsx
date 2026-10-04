import { useEffect, useState } from 'react'
import type { BudgetStatus, SavingsGoalProgress } from '../types/budget'
import {
  fetchBudgetStatus, createBudget, deleteBudget,
  fetchSavingsGoals, createSavingsGoal, updateSavingsGoal, deleteSavingsGoal,
} from '../api/budgets'
import Badge from './Badge'

function formatCurrency(amount: number): string {
  return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

function ProgressBar({ percent, danger = false }: { percent: number; danger?: boolean }) {
  const clamped = Math.min(percent, 100)
  const color = danger ? 'bg-red-500' : percent > 90 ? 'bg-amber-500' : 'bg-slate-700'
  return (
    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
      <div className={`h-full ${color} transition-all`} style={{ width: `${clamped}%` }} />
    </div>
  )
}

function BudgetForm({ onAdd }: { onAdd: (category: string, limit: number) => void }) {
  const [category, setCategory] = useState('')
  const [limit, setLimit] = useState('')

  const submit = () => {
    const parsed = parseFloat(limit)
    if (!category.trim() || !parsed || parsed <= 0) return
    onAdd(category.trim(), parsed)
    setCategory('')
    setLimit('')
  }

  return (
    <div className="flex gap-2 mt-3">
      <input
        placeholder="Category"
        value={category}
        onChange={(e) => setCategory(e.target.value)}
        className="border border-slate-200 rounded-md px-3 py-1.5 text-sm flex-1"
      />
      <input
        placeholder="Monthly limit"
        type="number"
        value={limit}
        onChange={(e) => setLimit(e.target.value)}
        className="border border-slate-200 rounded-md px-3 py-1.5 text-sm w-32"
      />
      <button onClick={submit} className="bg-slate-800 text-white px-3 py-1.5 rounded-md text-sm hover:bg-slate-700">
        Add
      </button>
    </div>
  )
}

function GoalForm({ onAdd }: { onAdd: (name: string, target: number, saved: number, contribution?: number) => void }) {
  const [name, setName] = useState('')
  const [target, setTarget] = useState('')
  const [saved, setSaved] = useState('')
  const [contribution, setContribution] = useState('')

  const submit = () => {
    const parsedTarget = parseFloat(target)
    const parsedSaved = parseFloat(saved) || 0
    if (!name.trim() || !parsedTarget || parsedTarget <= 0) return
    const parsedContribution = parseFloat(contribution)
    onAdd(name.trim(), parsedTarget, parsedSaved, parsedContribution > 0 ? parsedContribution : undefined)
    setName('')
    setTarget('')
    setSaved('')
    setContribution('')
  }

  return (
    <div className="flex flex-wrap gap-2 mt-3">
      <input placeholder="Goal name" value={name} onChange={(e) => setName(e.target.value)}
        className="border border-slate-200 rounded-md px-3 py-1.5 text-sm flex-1 min-w-[120px]" />
      <input placeholder="Target ₹" type="number" value={target} onChange={(e) => setTarget(e.target.value)}
        className="border border-slate-200 rounded-md px-3 py-1.5 text-sm w-28" />
      <input placeholder="Already saved ₹" type="number" value={saved} onChange={(e) => setSaved(e.target.value)}
        className="border border-slate-200 rounded-md px-3 py-1.5 text-sm w-32" />
      <input placeholder="Monthly ₹ (optional)" type="number" value={contribution} onChange={(e) => setContribution(e.target.value)}
        className="border border-slate-200 rounded-md px-3 py-1.5 text-sm w-36" />
      <button onClick={submit} className="bg-slate-800 text-white px-3 py-1.5 rounded-md text-sm hover:bg-slate-700">
        Add Goal
      </button>
    </div>
  )
}

export default function BudgetsAndGoals() {
  const [budgets, setBudgets] = useState<BudgetStatus[]>([])
  const [goals, setGoals] = useState<SavingsGoalProgress[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const loadAll = () => {
    setLoading(true)
    Promise.all([fetchBudgetStatus(), fetchSavingsGoals()])
      .then(([b, g]) => {
        setBudgets(b)
        setGoals(g)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }

  useEffect(loadAll, [])

  const handleAddBudget = async (category: string, monthly_limit: number) => {
    try {
      await createBudget(category, monthly_limit)
      loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add budget')
    }
  }

  const handleDeleteBudget = async (id: number) => {
    await deleteBudget(id)
    setBudgets((prev) => prev.filter((b) => b.id !== id))
  }

  const handleAddGoal = async (name: string, target_amount: number, saved_amount: number, monthly_contribution?: number) => {
    try {
      await createSavingsGoal({ name, target_amount, saved_amount, monthly_contribution })
      loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add goal')
    }
  }

  const handleAddToGoal = async (goal: SavingsGoalProgress, amount: number) => {
    try {
      const updated = await updateSavingsGoal(goal.id, goal.saved_amount + amount)
      setGoals((prev) => prev.map((g) => (g.id === goal.id ? updated : g)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update goal')
    }
  }

  const handleDeleteGoal = async (id: number) => {
    await deleteSavingsGoal(id)
    setGoals((prev) => prev.filter((g) => g.id !== id))
  }

  if (loading) return <p className="p-6 text-slate-400 text-sm">Loading...</p>

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {error && <div className="text-red-600 bg-red-50 rounded-md px-4 py-2 text-sm">{error}</div>}

      {/* Budgets */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-100 p-4">
        <h2 className="text-slate-700 font-medium mb-3 flex items-center gap-2">Category Budgets <Badge kind="actual" small>Actual spend</Badge></h2>
        {budgets.length === 0 ? (
          <p className="text-slate-400 text-sm">No budgets set yet.</p>
        ) : (
          <div className="space-y-4">
            {budgets.map((b) => (
              <div key={b.id}>
                <div className="flex justify-between items-baseline text-sm mb-1">
                  <span className="text-slate-700 font-medium">{b.category}</span>
                  <span className={b.over_budget ? 'text-red-600' : 'text-slate-500'}>
                    {formatCurrency(b.spent)} / {formatCurrency(b.monthly_limit)} ({b.utilization_percent}%)
                  </span>
                  <button onClick={() => handleDeleteBudget(b.id)} className="text-red-400 hover:text-red-600 text-xs ml-2">
                    Remove
                  </button>
                </div>
                <ProgressBar percent={b.utilization_percent} danger={b.over_budget} />
                {b.over_budget && (
                  <p className="text-red-500 text-xs mt-1">
                    Over budget by {formatCurrency(Math.abs(b.remaining))}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
        <BudgetForm onAdd={handleAddBudget} />
      </div>

      {/* Savings Goals */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-100 p-4">
        <h2 className="text-slate-700 font-medium mb-3 flex items-center gap-2">Savings Goals <Badge kind="actual" small>Actual progress</Badge> <Badge kind="projected" small>Time estimate</Badge></h2>
        {goals.length === 0 ? (
          <p className="text-slate-400 text-sm">No savings goals yet.</p>
        ) : (
          <div className="space-y-4">
            {goals.map((g) => (
              <div key={g.id}>
                <div className="flex justify-between items-baseline text-sm mb-1">
                  <span className="text-slate-700 font-medium">{g.name}</span>
                  <span className="text-slate-500">
                    {formatCurrency(g.saved_amount)} / {formatCurrency(g.target_amount)} ({g.progress_percent}%)
                  </span>
                  <button onClick={() => handleDeleteGoal(g.id)} className="text-red-400 hover:text-red-600 text-xs ml-2">
                    Remove
                  </button>
                </div>
                <ProgressBar percent={g.progress_percent} />
                <div className="flex justify-between items-center mt-1">
                  <p className="text-slate-400 text-xs">
                    {g.estimated_months_to_complete !== null
                      ? `~${g.estimated_months_to_complete} months left — ${g.estimation_note}`
                      : g.estimation_note}
                  </p>
                  <button
                    onClick={() => handleAddToGoal(g, 1000)}
                    className="text-slate-500 hover:text-slate-700 text-xs underline decoration-dotted"
                  >
                    +₹1,000
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        <GoalForm onAdd={handleAddGoal} />
      </div>
    </div>
  )
}
