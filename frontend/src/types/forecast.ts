// Mirrors backend/services/forecast_service.py response shape

export interface UpcomingExpense {
  merchant: string
  category: string | null
  expected_amount: number
  expected_date: string
}

export interface CashflowForecast {
  available: boolean
  reason?: string // present when available is false
  is_forecast?: boolean
  forecast_year?: number
  forecast_month?: number
  expected_income?: number
  expected_expenses?: number
  expected_savings?: number
  method?: string
  income_trend_confidence?: number | null
  expense_trend_confidence?: number | null
  based_on_months?: number
  upcoming_expenses?: UpcomingExpense[]
  upcoming_expenses_total?: number
}
