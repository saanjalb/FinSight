// Mirrors backend/schemas/transaction.py — kept in sync manually for now.
// If this project grows, generating these from the OpenAPI schema
// (FastAPI provides one automatically) would remove the duplication.

export interface Transaction {
  id: number
  date: string // ISO date string, e.g. "2026-09-15"
  merchant: string
  amount: number
  transaction_type: 'income' | 'expense'
  category: string | null
  description: string | null
  created_at: string
}

export interface TransactionFilters {
  category?: string
  search?: string
  date_from?: string
  date_to?: string
  min_amount?: number
  max_amount?: number
}

export interface ImportResult {
  imported: number
  skipped_duplicates?: number
  failed: number
  errors: string[]
  categorization?: {
    total_processed: number
    resolved_by_rule: number
    resolved_by_ml: number
    still_uncategorized: number
  }
}
