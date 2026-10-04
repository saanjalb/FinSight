import { API_BASE } from './transactions'

export interface ChatResponse {
  answer: string
  tools_used: string[]
}

export async function askFinanceAgent(message: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  const data = await res.json().catch(() => ({}))
  // Backend returns { detail: "..." } for known failures (missing key, rate limit)
  if (!res.ok) throw new Error(data.detail ?? `Request failed: ${res.status}`)
  return data
}
