import { useEffect, useState } from 'react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Legend,
} from 'recharts'
import type { Overview, CategorySpend, MonthlyTrendPoint, TopMerchant } from '../types/analytics'
import { fetchOverview, fetchSpendingByCategory, fetchMonthlyTrend, fetchTopMerchants } from '../api/analytics'
import Badge from './Badge'

const MONTH_NAMES = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// Distinct colors per category slice — repeats if there are more categories than colors.
const CATEGORY_COLORS = [
  '#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4',
  '#a855f7', '#ec4899', '#84cc16', '#64748b',
]

function formatCurrency(amount: number): string {
  return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

function SummaryCard({ label, value, tone = 'default' }: { label: string; value: string; tone?: 'default' | 'positive' | 'negative' }) {
  const toneClass = tone === 'positive' ? 'text-green-600' : tone === 'negative' ? 'text-red-500' : 'text-slate-800'
  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-100 p-4">
      <p className="text-slate-500 text-xs mb-1">{label}</p>
      <p className={`text-xl font-semibold ${toneClass}`}>{value}</p>
    </div>
  )
}

export default function Dashboard() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [categories, setCategories] = useState<CategorySpend[]>([])
  const [trend, setTrend] = useState<MonthlyTrendPoint[]>([])
  const [merchants, setMerchants] = useState<TopMerchant[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      fetchOverview(),
      fetchSpendingByCategory(),
      fetchMonthlyTrend(6),
      fetchTopMerchants(5),
    ])
      .then(([ov, cats, tr, merch]) => {
        setOverview(ov)
        setCategories(cats)
        setTrend(tr)
        setMerchants(merch)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load dashboard'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="p-6 text-slate-400 text-sm">Loading dashboard...</p>
  if (error) return <p className="p-6 text-red-600 bg-red-50 rounded-md mx-6 text-sm">{error}</p>
  if (!overview) return null

  const trendData = trend.map((t) => ({
    name: `${MONTH_NAMES[t.month]} ${t.year}`,
    Income: t.income,
    Expenses: t.expenses,
  }))

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800 flex items-center gap-3">
          Overview — {MONTH_NAMES[overview.month]} {overview.year}
          <Badge kind="actual" />
        </h1>
        <p className="text-slate-500 text-sm">{overview.transaction_count} transactions this month</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard label="Income" value={formatCurrency(overview.income)} tone="positive" />
        <SummaryCard label="Expenses" value={formatCurrency(overview.expenses)} />
        <SummaryCard label="Savings" value={formatCurrency(overview.savings)} tone={overview.savings >= 0 ? 'positive' : 'negative'} />
        <SummaryCard label="Savings Rate" value={`${overview.savings_rate_percent}%`} tone={overview.savings_rate_percent >= 20 ? 'positive' : 'default'} />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Category breakdown */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-100 p-4">
          <h2 className="text-slate-700 font-medium mb-3 text-sm">Spending by Category</h2>
          {categories.length === 0 ? (
            <p className="text-slate-400 text-sm">No expense data yet.</p>
          ) : (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="60%" height={220}>
                <PieChart>
                  <Pie data={categories} dataKey="amount" nameKey="category" innerRadius={45} outerRadius={80}>
                    {categories.map((_, i) => (
                      <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                </PieChart>
              </ResponsiveContainer>
              <ul className="text-xs space-y-1.5 flex-1">
                {categories.map((c, i) => (
                  <li key={c.category} className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 text-slate-600">
                      <span
                        className="inline-block w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: CATEGORY_COLORS[i % CATEGORY_COLORS.length] }}
                      />
                      {c.category}
                    </span>
                    <span className="text-slate-800 font-medium">{formatCurrency(c.amount)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Monthly trend */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-100 p-4">
          <h2 className="text-slate-700 font-medium mb-3 text-sm">Income vs Expenses (6 months)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value: number) => formatCurrency(value)} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="Income" stroke="#22c55e" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="Expenses" stroke="#ef4444" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top merchants */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-100 p-4">
        <h2 className="text-slate-700 font-medium mb-3 text-sm">Top Merchants This Month</h2>
        {merchants.length === 0 ? (
          <p className="text-slate-400 text-sm">No expense data yet.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {merchants.map((m) => (
              <li key={m.merchant} className="flex items-center justify-between py-2 text-sm">
                <span className="text-slate-700">{m.merchant}</span>
                <span className="text-slate-500 text-xs">{m.transaction_count} txns</span>
                <span className="text-slate-800 font-medium">{formatCurrency(m.total)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
