# FinSight — Presentation Guide

## One-line pitch
"I started with an ordinary finance app — transactions and charts — and layered on analytics,
machine learning and generative AI, with one rule: **the AI never does the maths.**"

## The story arc (say this in order)
1. **Foundation:** transactions, dashboard, budgets — plain full-stack (React, FastAPI, SQLite).
2. **Analytics + ML:** categorization (rules → ML), subscription and spending-leak detection, forecast.
3. **GenAI, done safely:** an agent that calls tools instead of guessing; an LLM that only parses
   what-if requests; RAG that answers only from documents and shows its sources.
4. **Trust:** every screen labels *Actual / Projected / Scenario / AI-generated*.

## Before you present (10 minutes)
- [ ] `python demo_check.py` → all PASS (WARN on AI checks = re-run once; free tier is rate-limited).
- [ ] Delete `backend/db/finsight.db` for a clean start; start backend + frontend.
- [ ] Ask one Learn question beforehand so the embeddings are cached.
- [ ] Wi-Fi works (AI tabs need internet). **Record a 2-minute screen video as a backup.**
- [ ] Don't fire many AI questions in a row — free-tier rate limit. Pause ~5 s between them.

## Demo run-order (~8 minutes)

| # | Do this | Say / point at | Expect (sample data) |
|---|---|---|---|
| 1 | **Transactions → Import CSV** → `sample_uncategorized.csv` | "305 rows, ~160 with no category." Read the green message | Imported 305 · auto-categorized 159 (158 by rules, 1 by ML) · 1 left uncategorized |
| 1b | Import the **same file again** | "Re-importing is safe" | 0 imported · 305 duplicates skipped |
| 2 | **Dashboard** | Green **Actual** badge. Savings rate trend | Sep: income ₹52,000, expenses ₹42,125, savings rate **19%** (was 36% in April) |
| 3 | Back in Transactions: search `ZEPTO` / `MYSTERY` | Rules matched most; ML caught ZEPTO → Food; MYSTERY left blank rather than guessed | ZEPTO = Food & Dining; MYSTERY = — |
| 4 | **Budgets & Goals**: add budget *Food & Dining* ₹8,000; goal *New Laptop* ₹80,000 / ₹35,000 | Budget bar goes red. Goal shows a **Projected** time estimate | Food 167% used, over by ₹5,380 · goal ≈ 3.7 months |
| 5 | **Insights** | Spending alerts (**Actual**, detected by statistics, no AI), upcoming payments and forecast (**Projected**) | Food +69.8% vs August · 7 recurring payments · Oct forecast savings ≈ ₹8,837 |
| 6 | **Ask FinSight**: "Why did my spending increase this month?" | Point at **Data from: …** — "it looked this up with tools; it can't invent numbers" | Cites the food increase (₹7,880 → ₹13,380) |
| 7 | **What-If**: "What if I reduce food spending by 20%?" | The violet chip shows what the AI *understood*; everything below is backend arithmetic; amber **Scenario** badge | Saves ₹1,871/mo, ₹22,450/yr · savings rate 23.5% → 27.1% |
| 7b | "What if I cancel Netflix and Spotify?" / "save ₹5,000 more per month" | Second shows goal timeline change | ₹768/mo (₹9,216/yr) · laptop goal 3.7 → 2.6 months |
| 8 | **Learn**: "What is compound interest?" | Show the **sources** under the answer | Cites *Compound Interest* |
| 8b | Learn: "Who won the cricket world cup?" | "It refuses rather than guess" | "Not in notes" |

If an AI step fails on stage: say "free-tier rate limit", wait a few seconds, retry once, then
switch to the backup video. The non-AI tabs don't depend on the network.

## Design decisions (and why)
1. **Tools, not free text.** The agent has 8 fixed tools that call tested backend functions, so a
   number in an answer always traces back to real data. The UI shows which tools were used.
2. **LLM only parses what-ifs.** A strict JSON schema, real category/subscription names in the
   prompt, and validation before use. A made-up category ("Pets") is rejected with a clear message.
3. **Rules → ML → (LLM later).** Cheapest reliable method first. ML only runs when rules can't
   decide, and low confidence means "leave it blank".
4. **Baseline = 3-month average** in scenarios, so one unusual month (the food spike) doesn't distort the "before".
5. **RAG without a vector database.** 24 chunks fit in memory; a numpy dot product is exact and
   simple. A vector DB would replace one method (`KnowledgeIndex.search`) if the notes grew to thousands.
6. **`NOT_COVERED` instead of a similarity cutoff** for RAG: no threshold to mis-tune, and the model must refuse rather than use outside knowledge.
7. **Duplicate-safe import** and **"this month" = latest month with data**, so the demo can't break by re-clicking or by presenting in a later month.

## Likely questions — honest answers
- **"Why not let the LLM calculate?"** LLMs can be confidently wrong at arithmetic. Here the maths is deterministic and testable; the LLM only chooses tools and words.
- **"What if the model hallucinates?"** Numbers only arrive via tool results; RAG answers must cite notes or refuse; scenario parameters are validated. It can still phrase things badly — that's why tool names/sources are shown.
- **"Why Gemini?"** It has a real free tier (no credit card, no expiry) and supports tool calling and structured output. The AI layer is isolated in `backend/ai/`, so switching provider is a contained change.
- **"Is user data safe?"** Demo data is synthetic. On the free tier Google may use prompts to improve models, so real financial data would need a paid/enterprise tier or a self-hosted model.
- **"How accurate is the forecast?"** It's a linear trend on ~6 monthly points. Shown with a fit score and labelled *Projected*. With under 3 months it falls back to an average and says so.
- **"How would you take this to production?"** PostgreSQL, authentication and per-user data, migrations (Alembic), real bank-statement parsers, an evaluation set for the agent and RAG, monitoring of LLM cost and failures.
- **"What didn't work / what did you learn?"** Testing found real bugs: re-importing doubled every transaction; "this month" was empty when data ended in the previous month; the agent didn't know today's date so "last month" was a guess; a demo screen showed an alarming alert on the "Uncategorized" bucket. Each got a fix and a check in `demo_check.py`.
- **"Did you use AI to build this?"** If yes, say so plainly. What matters is that you can explain every layer — use the architecture section of the README to rehearse.

## Numbers you may quote (sample data)
Sep expenses ₹42,125 · savings rate 36% → 19% (Apr → Sep) · food ₹7,880 → ₹13,380 (+69.8%) ·
food budget 167% used · 7 recurring payments (₹20,443 due next month) · subscriptions ₹2,398/mo ·
20% food cut = ₹1,871/mo.
