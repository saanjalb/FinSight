import type { ReactNode } from 'react'

/**
 * The four kinds of numbers/text FinSight shows. Every screen labels what
 * it displays with exactly one of these so a viewer can never mistake a
 * projection or an AI answer for a real transaction total.
 *
 *  actual     - computed from your real transactions
 *  projected  - a statistical forecast of the future
 *  scenario   - a hypothetical "what if", not real
 *  ai         - text written by the language model
 */
export type BadgeKind = 'actual' | 'projected' | 'scenario' | 'ai'

export const BADGES: Record<BadgeKind, { label: string; meaning: string; style: string }> = {
  actual: { label: 'Actual', meaning: 'from your real transactions', style: 'bg-emerald-50 text-emerald-700' },
  projected: { label: 'Projected', meaning: 'statistical forecast, not real yet', style: 'bg-sky-50 text-sky-700' },
  scenario: { label: 'Scenario', meaning: 'hypothetical what-if', style: 'bg-amber-50 text-amber-700' },
  ai: { label: 'AI-generated', meaning: 'written by the AI model', style: 'bg-violet-50 text-violet-700' },
}

export default function Badge({ kind, small = false, children }: { kind: BadgeKind; small?: boolean; children?: ReactNode }) {
  const b = BADGES[kind]
  return (
    <span
      title={b.meaning}
      className={`inline-block rounded-full font-medium whitespace-nowrap ${b.style} ${small ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5'}`}
    >
      {children ?? b.label}
    </span>
  )
}
