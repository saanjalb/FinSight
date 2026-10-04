import { API_BASE } from './transactions'
import type { Overview, CategorySpend, MonthlyTrendPoint, TopMerchant } from '../types/analytics'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`Analytics request failed: ${res.status}`)
  return res.json()
}

export const fetchOverview = () => get<Overview>('/api/analytics/overview')
export const fetchSpendingByCategory = () => get<CategorySpend[]>('/api/analytics/by-category')
export const fetchMonthlyTrend = (numMonths = 6) =>
  get<MonthlyTrendPoint[]>(`/api/analytics/monthly-trend?num_months=${numMonths}`)
export const fetchTopMerchants = (limit = 5) =>
  get<TopMerchant[]>(`/api/analytics/top-merchants?limit=${limit}`)
