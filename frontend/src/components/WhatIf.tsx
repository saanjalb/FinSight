import { useState } from 'react'
import type { ScenarioResult } from '../types/scenario'
import { askScenario } from '../api/scenarios'
import Badge from './Badge'

const EXAMPLES = [
  'What if I reduce food spending by 20%?',
  'What if I save ₹5,000 more per month?',
  'What if I cancel Netflix and Spotify?',
]

const inr = (n: number) => `₹${Math.round(n).toLocaleString('en-IN')}`

function describeUnderstanding(u: NonNullable<ScenarioResult['understood_as']>): string {
  if (u.scenario_type === 'reduce_category') return `reduce "${u.category}" by ${u.percent}%`
  if (u.scenario_type === 'increase_savings') return `save ${inr(u.amount ?? 0)} more per month`
  return `cancel ${(u.merchants ?? []).join(', ')}`
}

export default function WhatIf() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ScenarioResult | null>(null)

  const run = async (text: string) => {
    const q = text.trim()
    if (!q || loading) return
    setInput(q)
    setLoading(true)
    setError(null)
    try {
      setResult(await askScenario(q))
    } catch (err) {
      setResult(null)
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-semibold text-slate-800">What-If Simulator</h1>
      <p className="text-slate-500 text-sm mb-4">
        AI reads your question and picks the parameters. All numbers are calculated by the app, not the AI.
      </p>

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && run(input)}
          placeholder="What if I reduce food spending by 20%?"
          className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm"
        />
        <button
          onClick={() => run(input)}
          disabled={loading || !input.trim()}
          className="bg-slate-800 text-white px-4 py-2 rounded-lg text-sm hover:bg-slate-700 disabled:opacity-40"
        >
          {loading ? 'Simulating...' : 'Simulate'}
        </button>
      </div>
      <div className="flex flex-wrap gap-2 mt-3">
        {EXAMPLES.map((q) => (
          <button key={q} onClick={() => run(q)} className="text-xs border border-slate-200 rounded-full px-3 py-1.5 text-slate-600 hover:bg-slate-50">
            {q}
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-red-600 bg-red-50 rounded-md px-4 py-2 text-sm">{error}</p>}

      {result && (
        <div className="mt-5 bg-white rounded-lg shadow-sm border border-slate-100 p-5">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-slate-800 font-semibold">{result.title}</h2>
            <Badge kind="scenario">Scenario · hypothetical</Badge>
          </div>
          {result.understood_as && (
            <p className="text-xs text-slate-400 mb-4">
              <span className="mr-1.5"><Badge kind="ai" small>AI understood</Badge></span>
              {describeUnderstanding(result.understood_as)}
            </p>
          )}

          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-slate-50 rounded-md p-3">
              <p className="text-slate-400 text-xs">You'd save per month</p>
              <p className="text-green-600 text-xl font-semibold">{inr(result.monthly_difference)}</p>
            </div>
            <div className="bg-slate-50 rounded-md p-3">
              <p className="text-slate-400 text-xs">You'd save per year</p>
              <p className="text-green-600 text-xl font-semibold">{inr(result.annual_difference)}</p>
            </div>
          </div>

          <table className="w-full text-sm mb-4">
            <thead className="text-slate-400 text-xs text-left">
              <tr><th className="py-1 font-medium"></th><th className="font-medium text-right">Actual (avg of {result.baseline.months_used} mo)</th><th className="font-medium text-right">Scenario</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr><td className="py-1.5 text-slate-600">Monthly expenses</td><td className="text-right">{inr(result.baseline.avg_monthly_expenses)}</td><td className="text-right font-medium">{inr(result.scenario.avg_monthly_expenses)}</td></tr>
              <tr><td className="py-1.5 text-slate-600">Monthly savings</td><td className="text-right">{inr(result.baseline.avg_monthly_savings)}</td><td className="text-right font-medium">{inr(result.scenario.avg_monthly_savings)}</td></tr>
              <tr><td className="py-1.5 text-slate-600">Savings rate</td><td className="text-right">{result.baseline.savings_rate_percent}%</td><td className="text-right font-medium">{result.scenario.savings_rate_percent}%</td></tr>
            </tbody>
          </table>

          {result.details.category && (
            <p className="text-xs text-slate-500 mb-2">
              {result.details.category}: {inr(result.details.current_monthly_spend ?? 0)} → {inr(result.details.new_monthly_spend ?? 0)} per month
            </p>
          )}
          {result.details.cancelled && (
            <p className="text-xs text-slate-500 mb-2">
              Cancelled: {result.details.cancelled.map((c) => `${c.merchant} (${inr(c.monthly_amount)})`).join(', ')}
              {result.details.not_found && result.details.not_found.length > 0 && (
                <span className="text-amber-600"> · not found: {result.details.not_found.join(', ')}</span>
              )}
            </p>
          )}
          {result.details.goal_impact && result.details.goal_impact.length > 0 && (
            <ul className="text-xs text-slate-500 mb-2">
              {result.details.goal_impact.map((g) => (
                <li key={g.goal}>{g.goal}: ~{g.months_before} → ~{g.months_after} months to reach</li>
              ))}
            </ul>
          )}

          <ul className="text-xs text-slate-400 list-disc pl-4 mt-3 space-y-0.5">
            {result.assumptions.map((a) => <li key={a}>{a}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}
