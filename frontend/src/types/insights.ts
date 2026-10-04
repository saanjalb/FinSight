// Mirrors backend/services/subscription_service.py and leak_detection_service.py

export interface RecurringPayment {
  merchant: string
  category: string | null
  average_amount: number
  latest_amount: number
  occurrences: number
  distinct_months: number
  estimated_cycle_days: number
  last_charged: string
  next_expected: string
  days_until_next: number
  is_upcoming: boolean
  amount_changed: boolean
  amount_change_percent: number
}

export interface DuplicateSubscriptionGroup {
  category: string
  merchant_count: number
  merchants: { merchant: string; average_amount: number }[]
  total_monthly_cost: number
  explanation: string
}

export interface SpendingLeak {
  type: string
  category: string
  severity: 'low' | 'medium' | 'high'
  explanation: string
  [key: string]: unknown // detector-specific numeric fields vary by leak type
}

export interface SpendingLeaks {
  category_increases: SpendingLeak[]
  frequent_small_purchases: SpendingLeak[]
  unusual_category_spending: SpendingLeak[]
}
