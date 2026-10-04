import { API_BASE } from './transactions'

export interface KnowledgeSource {
  title: string
  section: string
  snippet: string
  similarity: number
}

export interface KnowledgeAnswer {
  answer: string
  grounded: boolean
  sources: KnowledgeSource[]
}

export async function askKnowledge(question: string): Promise<KnowledgeAnswer> {
  const res = await fetch(`${API_BASE}/api/knowledge/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail ?? `Request failed: ${res.status}`)
  return data
}
