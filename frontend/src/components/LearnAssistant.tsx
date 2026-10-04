import { useState } from 'react'
import { askKnowledge, type KnowledgeAnswer } from '../api/knowledge'
import Badge from './Badge'

const EXAMPLES = [
  'What is compound interest?',
  'How big should my emergency fund be?',
  'What is a SIP?',
  'Explain the 50/30/20 rule',
  'What is the difference between fixed and variable expenses?',
]

export default function LearnAssistant() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ question: string; data: KnowledgeAnswer } | null>(null)

  const ask = async (text: string) => {
    const q = text.trim()
    if (!q || loading) return
    setInput(q)
    setLoading(true)
    setError(null)
    try {
      setResult({ question: q, data: await askKnowledge(q) })
    } catch (err) {
      setResult(null)
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-semibold text-slate-800">Learn</h1>
      <p className="text-slate-500 text-sm mb-4">
        Finance basics, answered only from a small set of educational notes. Sources are shown under every answer.
        This is general education, not personal financial advice.
      </p>

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && ask(input)}
          placeholder="What is compound interest?"
          className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm"
        />
        <button
          onClick={() => ask(input)}
          disabled={loading || !input.trim()}
          className="bg-slate-800 text-white px-4 py-2 rounded-lg text-sm hover:bg-slate-700 disabled:opacity-40"
        >
          {loading ? 'Searching...' : 'Ask'}
        </button>
      </div>
      <div className="flex flex-wrap gap-2 mt-3">
        {EXAMPLES.map((q) => (
          <button key={q} onClick={() => ask(q)} className="text-xs border border-slate-200 rounded-full px-3 py-1.5 text-slate-600 hover:bg-slate-50">
            {q}
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-red-600 bg-red-50 rounded-md px-4 py-2 text-sm">{error}</p>}

      {result && (
        <div className="mt-5 bg-white rounded-lg shadow-sm border border-slate-100 p-5">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-xs">{result.question}</p>
            {result.data.grounded ? (
              <Badge kind="ai">AI-generated · from notes</Badge>
            ) : (
              <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full font-medium">Not in notes</span>
            )}
          </div>
          <p className="text-slate-800 text-sm whitespace-pre-wrap">{result.data.answer}</p>

          {result.data.sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-100">
              <p className="text-xs font-medium text-slate-500 mb-2">Sources</p>
              <ul className="space-y-2">
                {result.data.sources.map((s, i) => (
                  <li key={i} className="bg-slate-50 rounded-md p-3">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-700 font-medium">{s.title} — {s.section}</span>
                      <span className="text-slate-400">match {Math.round(s.similarity * 100)}%</span>
                    </div>
                    <p className="text-xs text-slate-500">{s.snippet}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
