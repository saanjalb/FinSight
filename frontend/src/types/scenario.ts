// Mirrors backend/services/scenario_service.py output
export interface ScenarioSide {
  avg_monthly_expenses: number
  avg_monthly_savings: number
  savings_rate_percent: number
}

export interface ScenarioResult {
  is_scenario: true
  scenario_type: 'reduce_category' | 'increase_savings' | 'cancel_subscriptions'
  title: string
  baseline: ScenarioSide & { months_used: number; avg_monthly_income: number }
  scenario: ScenarioSide
  monthly_difference: number
  annual_difference: number
  assumptions: string[]
  details: {
    category?: string
    current_monthly_spend?: number
    new_monthly_spend?: number
    goal_impact?: { goal: string; remaining: number; months_before: number | null; months_after: number | null }[]
    cancelled?: { merchant: string; monthly_amount: number }[]
    not_found?: string[]
  }
  understood_as?: {
    scenario_type: string
    category: string | null
    percent: number | null
    amount: number | null
    merchants: string[] | null
  }
}
