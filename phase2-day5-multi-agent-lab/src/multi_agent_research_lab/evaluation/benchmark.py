"""Benchmark helpers for single-agent vs multi-agent."""

import re
from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def run_benchmark(
    run_name: str,
    query: str,
    runner: Runner,
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency and derive lightweight lab metrics."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=_sum_cost(state),
        quality_score=_extract_quality_score(state),
        notes=_build_notes(state),
    )
    return state, metrics


def _sum_cost(state: ResearchState) -> float | None:
    costs: list[float] = []
    for result in state.agent_results:
        cost = result.metadata.get("estimated_cost_usd")
        if cost is not None:
            costs.append(float(cost))
    if not costs:
        return None
    return float(sum(costs))


def _extract_quality_score(state: ResearchState) -> float | None:
    for result in reversed(state.agent_results):
        match = re.search(r"quality score[^0-9]{0,20}(\d+(?:\.\d+)?)", result.content, re.I)
        if match:
            return min(10.0, max(0.0, float(match.group(1))))
    return None


def _build_notes(state: ResearchState) -> str:
    input_tokens = 0
    output_tokens = 0
    for result in state.agent_results:
        input_tokens += int(result.metadata.get("input_tokens") or 0)
        output_tokens += int(result.metadata.get("output_tokens") or 0)

    citation_coverage = _citation_coverage(state)
    failure_rate = 1.0 if state.errors else 0.0
    return (
        f"routes={state.route_history}; sources={len(state.sources)}; "
        f"tokens_in={input_tokens}; tokens_out={output_tokens}; "
        f"citation_coverage={citation_coverage:.2f}; "
        f"failure_rate={failure_rate:.2f}; errors={len(state.errors)}"
    )


def _citation_coverage(state: ResearchState) -> float:
    if not state.sources:
        return 0.0

    answer = state.final_answer or ""
    cited_source_numbers = {
        int(match.group(1))
        for match in re.finditer(r"\[(\d+)\]", answer)
        if int(match.group(1)) <= len(state.sources)
    }
    return len(cited_source_numbers) / len(state.sources)
