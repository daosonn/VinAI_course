# Design Template

## Problem

Build a research assistant that receives a user query, searches for relevant sources,
analyzes the evidence, writes a beginner-friendly final answer, and reviews the answer
before returning it.

Example query used in the benchmark:

```text
Explain multi-agent systems in 3 beginner-friendly bullets
```

## Why Multi-Agent?

A single-agent baseline can answer quickly, but it mixes several jobs in one prompt:
search interpretation, evidence selection, analysis, writing, and self-review. That makes
the reasoning harder to inspect and makes failures harder to debug.

The multi-agent design separates the work:

- Researcher focuses on source collection and research notes.
- Analyst focuses on trade-offs, evidence gaps, and answer structure.
- Writer focuses on final response quality and audience fit.
- Critic focuses on citation coverage, hallucination risk, and quality review.
- Supervisor keeps the workflow ordered and stops it safely.

This is useful for learning because each state transition can be inspected in the trace.

## Agent Roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Decide the next route and stop condition | Current `ResearchState` | Next route in `route_history` | Infinite loop or wrong route; controlled by `MAX_ITERATIONS` |
| Researcher | Search sources and write compact research notes | `request.query`, `request.max_sources` | `sources`, `research_notes` | Search API failure; falls back to mock sources |
| Analyst | Convert research notes into structured insight | `research_notes`, `sources` | `analysis_notes` | Missing/weak evidence; records an error or flags uncertainty |
| Writer | Produce the final user-facing answer | `research_notes`, `analysis_notes`, `sources` | `final_answer` | Unsupported claims or missing citations |
| Critic | Review final answer quality and citation coverage | `final_answer`, `sources` | Critic `AgentResult` with verdict and quality score | Overly lenient review; mitigated by explicit critic rubric |

## Shared State

The workflow passes one `ResearchState` object through all agents. Important fields:

- `request`: original query, audience, and max source count.
- `iteration`: number of supervisor routing decisions.
- `route_history`: ordered list of selected routes, used to explain the workflow.
- `sources`: source documents from Tavily or fallback mock search.
- `research_notes`: Researcher summary grounded in sources.
- `analysis_notes`: Analyst interpretation, trade-offs, and evidence gaps.
- `final_answer`: Writer output returned to the user.
- `agent_results`: per-agent outputs plus metadata such as token counts.
- `trace`: structured events and timing spans for debugging.
- `errors`: non-fatal failures or guardrail events.

## Routing Policy

Current route:

```text
start
  -> supervisor
  -> researcher
  -> supervisor
  -> analyst
  -> supervisor
  -> writer
  -> supervisor
  -> critic
  -> supervisor
  -> done
```

Supervisor logic:

1. If `iteration >= MAX_ITERATIONS`, route to `done`.
2. If `final_answer` exists and Critic has already run, route to `done`.
3. If `final_answer` exists but Critic has not run, route to `critic`.
4. If `sources` or `research_notes` are missing, route to `researcher`.
5. If `analysis_notes` is missing, route to `analyst`.
6. Otherwise, route to `writer`.

## Guardrails

- Max iterations: `MAX_ITERATIONS` from `.env`, default 6.
- Timeout: `TIMEOUT_SECONDS` from `.env`, used by OpenAI and Tavily clients.
- Retry: OpenAI calls use `tenacity` retry with exponential backoff.
- Fallback: Tavily search falls back to deterministic mock sources if the API key is missing or the request fails.
- Validation: Pydantic schemas validate `ResearchQuery`, `SourceDocument`, `AgentResult`, and `BenchmarkMetrics`.
- Secret handling: API keys are loaded from `.env` and `.env` is ignored by git.
- Traceability: each agent writes trace events and workflow spans.

## Benchmark Plan

Benchmark command:

```bash
python -m multi_agent_research_lab.cli benchmark \
  --query "Explain multi-agent systems in 3 beginner-friendly bullets"
```

Metrics:

| Metric | How measured | Expected outcome |
|---|---|---|
| Latency | Wall-clock time per run | Multi-agent is slower because it uses more LLM calls |
| Token usage | Sum of provider token counts in `agent_results.metadata` | Multi-agent uses more tokens |
| Quality | Critic score from final review | Multi-agent should expose quality review explicitly |
| Citation coverage | Number of citation markers in final answer divided by source count | Multi-agent should use source references |
| Failure rate | Number of errors in `state.errors` | Should be 0 for the successful benchmark query |

Artifacts:

- `reports/benchmark_report.md`: human-readable comparison.
- `reports/benchmark_trace.json`: full state and trace export for debugging.

## Failure Mode And Fix

Observed or expected failure modes:

- Search provider fails or key is missing: fallback mock sources keep the workflow runnable.
- LLM request times out: retry with exponential backoff; final failure surfaces as an exception.
- Supervisor loops forever: max iteration guard stops the workflow.
- Writer makes unsupported claims: Critic reviews citation coverage and hallucination risk.
- Benchmark quality score missing: report parser extracts the Critic quality score when available.
