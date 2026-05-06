"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(metrics: list[BenchmarkMetrics]) -> str:
    """Render benchmark metrics to markdown."""

    lines = [
        "# Benchmark Report",
        "",
        "## Summary",
        "",
        "| Run | Latency (s) | Cost (USD) | Quality | Notes |",
        "|---|---:|---:|---:|---|",
    ]
    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        lines.append(
            f"| {item.run_name} | {item.latency_seconds:.2f} | "
            f"{cost} | {quality} | {item.notes} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Baseline uses one LLM call to do the whole task.",
            "- Multi-agent splits the task into researcher, analyst, writer, and critic.",
            "- Latency is usually higher for multi-agent because it performs more calls.",
            "- Quality should be judged by source use, clarity, and critic findings.",
            "- Citation coverage and failure rate are included in the Notes column.",
            "",
            "## Failure Modes And Fixes",
            "",
            "| Failure mode | Current guardrail |",
            "|---|---|",
            "| Search API key missing or Tavily request fails | "
            "Fall back to deterministic mock sources |",
            "| LLM request fails transiently | Retry with exponential backoff |",
            "| Workflow loops too long | Stop at `MAX_ITERATIONS` |",
            "| Writer includes weak or unsupported claims | "
            "Critic reviews citation coverage and hallucination risk |",
            "",
        ]
    )
    return "\n".join(lines)
