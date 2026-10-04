import type { Transaction, TransactionFilters, ImportResult } from '../types/transaction'

export const API_BASE = 'http://localhost:8000'

/**
 * All fetch calls live here rather than inside components. This keeps
 * components focused on rendering, and gives us one place to change
 * if the API base URL or error handling strategy changes later.
 */

function buildQueryString(filters: TransactionFilters): string {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value))
  })
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export async function fetchTransactions(filters: TransactionFilters = {}): Promise<Transaction[]> {
  const res = await fetch(`${API_BASE}/api/transactions/${buildQueryString(filters)}`)
  if (!res.ok) throw new Error(`Failed to fetch transactions: ${res.status}`)
  return res.json()
}

export async function updateTransactionCategory(id: number, category: string): Promise<Transaction> {
  const res = await fetch(`${API_BASE}/api/transactions/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category }),
  })
  if (!res.ok) throw new Error(`Failed to update transaction: ${res.status}`)
  return res.json()
}

export async function deleteTransaction(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/transactions/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Failed to delete transaction: ${res.status}`)
}

export async function importTransactionsCsv(file: File): Promise<ImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/api/transactions/import`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error(`Import failed: ${res.status}`)
  return res.json()
}
