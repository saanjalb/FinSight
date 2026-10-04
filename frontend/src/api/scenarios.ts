import { API_BASE } from './transactions'
import type { ScenarioResult } from '../types/scenario'

export async function askScenario(message: string): Promise<ScenarioResult> {
  const res = await fetch(`${API_BASE}/api/scenarios/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail ?? `Request failed: ${res.status}`)
  return data
}
