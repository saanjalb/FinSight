import { API_BASE } from './transactions'
import type { CashflowForecast } from '../types/forecast'

export async function fetchForecast(): Promise<CashflowForecast> {
  const res = await fetch(`${API_BASE}/api/forecast/next-month`)
  if (!res.ok) throw new Error(`Forecast request failed: ${res.status}`)
  return res.json()
}
