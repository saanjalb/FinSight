import { useEffect, useState } from 'react'
import type { Transaction, TransactionFilters } from '../types/transaction'
import {
  fetchTransactions,
  deleteTransaction,
  updateTransactionCategory,
  importTransactionsCsv,
} from '../api/transactions'
import Badge from './Badge'

export default function TransactionTable() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<TransactionFilters>({})
  const [importMessage, setImportMessage] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValue, setEditValue] = useState('')

  const loadTransactions = (activeFilters: TransactionFilters) => {
    setLoading(true)
    setError(null)
    fetchTransactions(activeFilters)
      .then(setTransactions)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadTransactions({})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const applyFilters = () => loadTransactions(filters)

  const clearFilters = () => {
    setFilters({})
    loadTransactions({})
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this transaction?')) return
    try {
      await deleteTransaction(id)
      setTransactions((prev) => prev.filter((t) => t.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  const startEditingCategory = (txn: Transaction) => {
    setEditingId(txn.id)
    setEditValue(txn.category ?? '')
  }

  const saveCategory = async (id: number) => {
    try {
      const updated = await updateTransactionCategory(id, editValue.trim())
      setTransactions((prev) => prev.map((t) => (t.id === id ? updated : t)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed')
    } finally {
      setEditingId(null)
    }
  }

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const result = await importTransactionsCsv(file)
      const c = result.categorization
      setImportMessage(
        [
          `Imported ${result.imported} transactions`,
          result.skipped_duplicates ? `${result.skipped_duplicates} duplicates skipped` : '',
          result.failed ? `${result.failed} rows failed` : '',
          c && c.total_processed > 0
            ? `auto-categorized ${c.resolved_by_rule + c.resolved_by_ml} (${c.resolved_by_rule} by rules, ${c.resolved_by_ml} by ML)` +
              (c.still_uncategorized ? `, ${c.still_uncategorized} left uncategorized` : '')
            : '',
        ]
          .filter(Boolean)
          .join(' · '),
      )
      loadTransactions(filters)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed')
    } finally {
      e.target.value = '' // allow re-selecting the same file
    }
  }

  const categories = Array.from(
    new Set(transactions.map((t) => t.category).filter((c): c is string => Boolean(c))),
  ).sort()

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800 flex items-center gap-3">Transactions <Badge kind="actual" /></h1>
          <p className="text-slate-500 text-sm">{transactions.length} transactions</p>
        </div>
        <label className="cursor-pointer bg-slate-800 text-white px-4 py-2 rounded-lg text-sm hover:bg-slate-700 transition">
          Import CSV
          <input type="file" accept=".csv" className="hidden" onChange={handleImport} />
        </label>
      </div>

      {importMessage && (
        <div className="mb-4 text-green-700 bg-green-50 rounded-md px-4 py-2 text-sm">
          {importMessage}
        </div>
      )}
      {error && (
        <div className="mb-4 text-red-600 bg-red-50 rounded-md px-4 py-2 text-sm">{error}</div>
      )}

      {/* Filter bar */}
      <div className="flex flex-wrap gap-3 mb-4 bg-white p-4 rounded-lg shadow-sm border border-slate-100">
        <input
          type="date"
          value={filters.date_from ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value }))}
          className="border border-slate-200 rounded-md px-3 py-1.5 text-sm"
        />
        <input
          type="date"
          value={filters.date_to ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value }))}
          className="border border-slate-200 rounded-md px-3 py-1.5 text-sm"
        />
        <select
          value={filters.category ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value || undefined }))}
          className="border border-slate-200 rounded-md px-3 py-1.5 text-sm"
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search merchant or description..."
          value={filters.search ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
          className="border border-slate-200 rounded-md px-3 py-1.5 text-sm flex-1 min-w-[180px]"
        />
        <button
          onClick={applyFilters}
          className="bg-slate-800 text-white px-4 py-1.5 rounded-md text-sm hover:bg-slate-700"
        >
          Apply
        </button>
        <button
          onClick={clearFilters}
          className="border border-slate-200 px-4 py-1.5 rounded-md text-sm hover:bg-slate-50"
        >
          Clear
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-100 overflow-hidden">
        {loading ? (
          <p className="p-6 text-slate-400 text-sm">Loading...</p>
        ) : transactions.length === 0 ? (
          <p className="p-6 text-slate-400 text-sm">
            No transactions yet — import a CSV to get started.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-left">
              <tr>
                <th className="px-4 py-2 font-medium">Date</th>
                <th className="px-4 py-2 font-medium">Merchant</th>
                <th className="px-4 py-2 font-medium">Category</th>
                <th className="px-4 py-2 font-medium text-right">Amount</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {transactions.map((t) => (
                <tr key={t.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2 text-slate-600">{t.date}</td>
                  <td className="px-4 py-2 text-slate-800">{t.merchant}</td>
                  <td className="px-4 py-2 text-slate-500">
                    {editingId === t.id ? (
                      <input
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={() => saveCategory(t.id)}
                        onKeyDown={(e) => e.key === 'Enter' && saveCategory(t.id)}
                        className="border border-slate-300 rounded px-2 py-0.5 text-xs w-32"
                      />
                    ) : (
                      <button
                        onClick={() => startEditingCategory(t)}
                        className="hover:underline decoration-dotted"
                        title="Click to edit category"
                      >
                        {t.category ?? '—'}
                      </button>
                    )}
                  </td>
                  <td
                    className={`px-4 py-2 text-right font-medium ${
                      t.transaction_type === 'income' ? 'text-green-600' : 'text-slate-800'
                    }`}
                  >
                    {t.transaction_type === 'income' ? '+' : '-'}₹{t.amount.toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => handleDelete(t.id)}
                      className="text-red-500 hover:text-red-700 text-xs"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
