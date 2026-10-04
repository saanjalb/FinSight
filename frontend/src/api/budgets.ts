import { API_BASE } from './transactions'
import type { Budget, BudgetStatus, SavingsGoalProgress } from '../types/budget'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`Request failed: ${res.status}`)
  return res.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Request failed: ${res.status}`)
  return res.json()
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Request failed: ${res.status}`)
  return res.json()
}

async function del(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Request failed: ${res.status}`)
}

// Budgets
export const fetchBudgetStatus = () => get<BudgetStatus[]>('/api/budgets/status')
export const createBudget = (category: string, monthly_limit: number) =>
  post<Budget>('/api/budgets/', { category, monthly_limit })
export const updateBudget = (id: number, monthly_limit: number) =>
  patch<Budget>(`/api/budgets/${id}`, { monthly_limit })
export const deleteBudget = (id: number) => del(`/api/budgets/${id}`)

// Savings goals
export const fetchSavingsGoals = () => get<SavingsGoalProgress[]>('/api/savings-goals/')
export const createSavingsGoal = (data: {
  name: string
  target_amount: number
  saved_amount: number
  monthly_contribution?: number
}) => post<SavingsGoalProgress>('/api/savings-goals/', data)
export const updateSavingsGoal = (id: number, saved_amount: number) =>
  patch<SavingsGoalProgress>(`/api/savings-goals/${id}`, { saved_amount })
export const deleteSavingsGoal = (id: number) => del(`/api/savings-goals/${id}`)
