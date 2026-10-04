import { useEffect, useState } from 'react'
import type { CashflowForecast } from '../types/forecast'
import { fetchForecast } from '../api/forecast'
import Badge from './Badge'

const MONTH_NAMES = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function formatCurrency(amount: number): string {
  return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

export default function ForecastCard() {
  const [forecast, setForecast] = useState<CashflowForecast | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchForecast()
      .then(setForecast)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load forecast'))
  }, [])

  if (error) return <p className="text-red-600 bg-red-50 rounded-md px-4 py-2 text-sm">{error}</p>
  if (!forecast) return <p className="text-slate-400 text-sm">Loading forecast...</p>

  if (!forecast.available) {
    return <p className="text-slate-400 text-sm">{forecast.reason}</p>
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-100 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-slate-700 font-medium">
          {MONTH_NAMES[forecast.forecast_month!]} {forecast.forecast_year} Forecast
        </h2>
        {/* Explicit "this is a projection" badge — never to be mistaken for actuals */}
        <Badge kind="projected" />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-3">
        <div>
          <p className="text-slate-400 text-xs">Expected Income</p>
          <p className="text-slate-800 font-semibold">{formatCurrency(forecast.expected_income!)}</p>
        </div>
        <div>
          <p className="text-slate-400 text-xs">Expected Expenses</p>
          <p className="text-slate-800 font-semibold">{formatCurrency(forecast.expected_expenses!)}</p>
        </div>
        <div>
          <p className="text-slate-400 text-xs">Expected Savings</p>
          <p className={`font-semibold ${forecast.expected_savings! >= 0 ? 'text-green-600' : 'text-red-500'}`}>
            {formatCurrency(forecast.expected_savings!)}
          </p>
        </div>
      </div>

      <p className="text-slate-400 text-xs mb-3">
        {forecast.method}
        {forecast.income_trend_confidence !== null && forecast.income_trend_confidence !== undefined && (
          <> (income fit: {Math.round(forecast.income_trend_confidence * 100)}%, expense fit:{' '}
            {Math.round((forecast.expense_trend_confidence ?? 0) * 100)}%)</>
        )}
      </p>

      {forecast.upcoming_expenses && forecast.upcoming_expenses.length > 0 && (
        <div className="border-t border-slate-100 pt-3">
          <p className="text-slate-600 text-xs font-medium mb-2">
            Upcoming Expenses — {formatCurrency(forecast.upcoming_expenses_total ?? 0)} total
          </p>
          <ul className="space-y-1">
            {forecast.upcoming_expenses.map((e) => (
              <li key={e.merchant} className="flex justify-between text-xs text-slate-500">
                <span>{e.merchant}</span>
                <span>{formatCurrency(e.expected_amount)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
