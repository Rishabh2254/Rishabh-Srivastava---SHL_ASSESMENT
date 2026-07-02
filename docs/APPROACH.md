# Approach Document

## Problem Framing

Recruiters often know they need "an assessment" but not which SHL product fits. The agent must:

- Clarify with minimal turns (≤8)
- Recommend only verified Individual Test Solutions
- Support refinement and comparison without hallucination
- Refuse out-of-scope and adversarial requests

## Solution Strategy

### Context Engineering

We treat each `/chat` request as a **complete state reconstruction** problem:

1. Parse user turns into structured slots (role, seniority, skills, etc.)
2. Determine intent before any LLM call
3. Build a retrieval query from slots + latest user message
4. Inject only top-K catalog records into the prompt

This reduces token waste and prevents the model from "remembering" non-SHL products.

### Agent Design

Rather than a heavyweight multi-agent framework, we use a **single orchestrator** with explicit intent routing. This is easier to defend in interviews: every branch is readable Python, not opaque tool-calling traces.

| Intent | Behavior |
|--------|----------|
| CLARIFY | Rule-based next-question selection by slot priority |
| RECOMMEND | Hybrid retrieval → LLM JSON → validator |
| REFINE | Same as recommend with refinement instruction |
| COMPARE | Retrieve named products → LLM comparison, `recommendations=[]` |
| REFUSE | Static policy response for off-topic / injection |

### Retrieval Design

**Why not keyword-only?** Job descriptions use varied language; embeddings generalize better.

**Why hybrid?** Pure semantic search can miss exact technology tokens (e.g., "Java 8"). BM25 compensates.

**Why metadata boost?** User constraints like "remote" or "personality" are structured and cheap to score without another LLM call.

### Prompt Layering

1. **System** — identity, scope, refusal policy
2. **Conversation** — history, slots, intent, action
3. **Retrieval context** — labeled catalog entries with scores
4. **Format** — strict JSON schema for downstream validation

### Catalog Ingestion

Primary path: live scrape of SHL `type=1` catalog with detail enrichment.

Fallback: `scripts/bootstrap_catalog.py` transforms a public SHL-derived dataset when the live site blocks automated listing access (common with WAF/geo rules). Production deployments should prefer live scrape on a schedule.

## Evaluation Methodology

Recommended offline metrics:

| Metric | Definition |
|--------|------------|
| Recall@10 | Fraction of labeled relevant URLs in top 10 |
| Schema compliance | 100% responses match `ChatResponse` |
| Hallucination rate | % recommendations with URL ∉ catalog |
| Avg turns to recommend | Lower is better (target ≤3 for clear queries) |

Qualitative probes:

- Vague opener → must not recommend immediately
- "Include personality" → refinement without reset
- OPQ vs GSA → grounded comparison
- Prompt injection → polite refusal
- Salary/legal questions → scope refusal

## Tradeoffs

**FAISS vs ChromaDB**: FAISS chosen for zero-dependency deployment and fast startup on free tiers.

**Mock LLM default**: Enables CI and local demo without API spend; production should use Groq/Gemini.

**Rule-based clarification**: More predictable than LLM-only slot filling; may miss exotic phrasing — mitigated by retrieval on partial slots after turn 3.

## Future Work

- Cross-encoder reranking on top-50 candidates
- Scheduled catalog refresh + index rebuild
- Labeled evaluation set with automated Recall@10 CI gate
- Optional conversation summarization for very long histories

## Interview Talking Points

1. **Why RAG?** SHL catalog is large and changes; grounding beats parametric memory.
2. **Why validate after LLM?** Models violate constraints; validator is the trust boundary.
3. **Why stateless?** Simpler scaling, no session store, matches assignment API contract.
4. **Why hybrid ranking?** Recall and precision optimize different signals; weighted fusion is interpretable.
