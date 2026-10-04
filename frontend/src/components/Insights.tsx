import { useEffect, useState } from 'react'
import type { RecurringPayment, DuplicateSubscriptionGroup, SpendingLeaks } from '../types/insights'
import { fetchSubscriptions, fetchUpcomingPayments, fetchDuplicateSubscriptions, fetchSpendingLeaks } from '../api/insights'
import ForecastCard from './ForecastCard'
import Badge from './Badge'

function formatCurrency(amount: number): string {
  return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, string> = {
    high: 'bg-red-50 text-red-600',
    medium: 'bg-amber-50 text-amber-600',
    low: 'bg-slate-100 text-slate-600',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[severity] ?? styles.low}`}>
      {severity}
    </span>
  )
}

export default function Insights() {
  const [subscriptions, setSubscriptions] = useState<RecurringPayment[]>([])
  const [upcoming, setUpcoming] = useState<RecurringPayment[]>([])
  const [duplicates, setDuplicates] = useState<DuplicateSubscriptionGroup[]>([])
  const [leaks, setLeaks] = useState<SpendingLeaks | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      fetchSubscriptions(),
      fetchUpcomingPayments(10),
      fetchDuplicateSubscriptions(),
      fetchSpendingLeaks(),
    ])
      .then(([subs, up, dup, lk]) => {
        setSubscriptions(subs)
        setUpcoming(up)
        setDuplicates(dup)
        setLeaks(lk)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load insights'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="p-6 text-slate-400 text-sm">Loading insights...</p>
  if (error) return <p className="p-6 text-red-600 bg-red-50 rounded-md mx-6 text-sm">{error}</p>

  const allLeaks = leaks
    ? [...leaks.category_increases, ...leaks.frequent_small_purchases, ...leaks.unusual_category_spending]
    : []

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <ForecastCard />

      {/* Spending leak alerts — most actionable, shown first */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-100 p-4">
        <h2 className="text-slate-700 font-medium mb-3 flex items-center gap-2">Spending Alerts <Badge kind="actual" small>Detected from actuals</Badge></h2>
        {allLeaks.length === 0 ? (
          <p className="text-slate-400 text-sm">No unusual spending patterns detected.</p>
        ) : (
          <ul className="space-y-3">
            {allLeaks.map((leak, i) => (
              <li key={i} className="border border-slate-100 rounded-md p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-slate-700 text-sm font-medium">{leak.category}</span>
                  <SeverityBadge severity={leak.severity} />
                </div>
                <p className="text-slate-500 text-xs">{leak.explanation}</p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Upcoming payments */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-100 p-4">
          <h2 className="text-slate-700 font-medium mb-3 flex items-center gap-2">Upcoming Payments <Badge kind="projected" small>Expected</Badge></h2>
          {upcoming.length === 0 ? (
            <p className="text-slate-400 text-sm">Nothing due soon.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {upcoming.map((p) => (
                <li key={p.merchant} className="flex items-center justify-between py-2 text-sm">
                  <div>
                    <p className="text-slate-700">{p.merchant}</p>
                    <p className="text-slate-400 text-xs">in {p.days_until_next} days</p>
                  </div>
                  <span className="text-slate-800 font-medium">{formatCurrency(p.latest_amount)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Duplicate subscriptions */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-100 p-4">
          <h2 className="text-slate-700 font-medium mb-3">Overlapping Recurring Charges</h2>
          {duplicates.length === 0 ? (
            <p className="text-slate-400 text-sm">No overlapping categories detected.</p>
          ) : (
            <ul className="space-y-3">
              {duplicates.map((d) => (
                <li key={d.category} className="text-sm">
                  <p className="text-slate-700 font-medium">
                    {d.category} — {formatCurrency(d.total_monthly_cost)}/mo
                  </p>
                  <p className="text-slate-400 text-xs">{d.merchants.map((m) => m.merchant).join(', ')}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* All recurring payments */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-100 p-4">
        <h2 className="text-slate-700 font-medium mb-3 flex items-center gap-2">All Recurring Payments <Badge kind="actual" small>Detected from actuals</Badge></h2>
        <table className="w-full text-sm">
          <thead className="text-slate-500 text-left">
            <tr>
              <th className="py-1.5 font-medium">Merchant</th>
              <th className="py-1.5 font-medium">Category</th>
              <th className="py-1.5 font-medium text-right">Amount</th>
              <th className="py-1.5 font-medium text-right">Next Due</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {subscriptions.map((s) => (
              <tr key={s.merchant}>
                <td className="py-2 text-slate-700">{s.merchant}</td>
                <td className="py-2 text-slate-500">{s.category ?? '—'}</td>
                <td className="py-2 text-right text-slate-800 font-medium">
                  {formatCurrency(s.latest_amount)}
                  {s.amount_changed && (
                    <span className={s.amount_change_percent > 0 ? 'text-red-500' : 'text-green-600'}>
                      {' '}({s.amount_change_percent > 0 ? '+' : ''}{s.amount_change_percent}%)
                    </span>
                  )}
                </td>
                <td className="py-2 text-right text-slate-500 text-xs">{s.next_expected}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
