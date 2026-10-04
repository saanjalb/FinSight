// Mirrors backend/services/analytics_service.py response shapes.

export interface Overview {
  year: number
  month: number
  income: number
  expenses: number
  savings: number
  savings_rate_percent: number
  transaction_count: number
}

export interface CategorySpend {
  category: string
  amount: number
}

export interface MonthlyTrendPoint {
  year: number
  month: number
  income: number
  expenses: number
}

export interface TopMerchant {
  merchant: string
  total: number
  transaction_count: number
}
