// Mirrors backend/schemas/budget.py and savings_goal.py

export interface Budget {
  id: number
  category: string
  monthly_limit: number
  created_at: string
}

export interface BudgetStatus {
  id: number
  category: string
  monthly_limit: number
  spent: number
  utilization_percent: number
  remaining: number
  over_budget: boolean
}

export interface SavingsGoalProgress {
  id: number
  name: string
  target_amount: number
  saved_amount: number
  remaining: number
  progress_percent: number
  monthly_contribution: number | null
  estimated_months_to_complete: number | null
  estimation_note: string
}
