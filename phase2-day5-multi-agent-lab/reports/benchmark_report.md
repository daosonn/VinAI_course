# Benchmark Report

## Summary

| Run | Latency (s) | Cost (USD) | Quality | Notes |
|---|---:|---:|---:|---|
| single-agent-baseline | 8.22 |  |  | routes=[]; sources=5; tokens_in=1101; tokens_out=246; citation_coverage=1.00; failure_rate=0.00; errors=0 |
| multi-agent | 32.95 |  | 8.0 | routes=['researcher', 'analyst', 'writer', 'critic', 'done']; sources=5; tokens_in=4226; tokens_out=1512; citation_coverage=1.00; failure_rate=0.00; errors=0 |

## Interpretation

- Baseline uses one LLM call to do the whole task.
- Multi-agent splits the task into researcher, analyst, writer, and critic.
- Latency is usually higher for multi-agent because it performs more calls.
- Quality should be judged by source use, clarity, and critic findings.
- Citation coverage and failure rate are included in the Notes column.

## Failure Modes And Fixes

| Failure mode | Current guardrail |
|---|---|
| Search API key missing or Tavily request fails | Fall back to deterministic mock sources |
| LLM request fails transiently | Retry with exponential backoff |
| Workflow loops too long | Stop at `MAX_ITERATIONS` |
| Writer includes weak or unsupported claims | Critic reviews citation coverage and hallucination risk |
