import { API_BASE } from './transactions'
import type { RecurringPayment, DuplicateSubscriptionGroup, SpendingLeaks } from '../types/insights'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`Request failed: ${res.status}`)
  return res.json()
}

export const fetchSubscriptions = () => get<RecurringPayment[]>('/api/insights/subscriptions')
export const fetchUpcomingPayments = (withinDays = 10) =>
  get<RecurringPayment[]>(`/api/insights/upcoming-payments?within_days=${withinDays}`)
export const fetchDuplicateSubscriptions = () =>
  get<DuplicateSubscriptionGroup[]>('/api/insights/duplicate-subscriptions')
export const fetchSpendingLeaks = () => get<SpendingLeaks>('/api/insights/spending-leaks')
