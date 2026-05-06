"""Command-line entrypoint for the lab starter."""

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


def _run_single_agent_baseline(query: str) -> ResearchState:
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)
    sources = SearchClient().search(query, max_results=request.max_sources)
    source_context = "\n".join(
        f"[{index}] {source.title}\nURL: {source.url or 'N/A'}\nSnippet: {source.snippet}"
        for index, source in enumerate(sources, start=1)
    )
    response = LLMClient().complete(
        system_prompt=(
            "You are a single-agent research assistant. Answer the user directly "
            "using the provided sources. Use citation markers like [1]."
        ),
        user_prompt=(
            f"Query: {query}\n"
            f"Audience: {request.audience}\n\n"
            f"Sources:\n{source_context}\n\n"
            "Write a clear answer and include a limitations note."
        ),
    )
    state.sources = sources
    state.final_answer = response.content
    state.agent_results.append(
        AgentResult(
            agent=AgentName.WRITER,
            content=response.content,
            metadata={
                "mode": "single_agent_baseline",
                "source_count": len(sources),
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "estimated_cost_usd": response.cost_usd,
            },
        )
    )
    state.add_trace_event(
        "baseline.single_agent",
        {
            "source_count": len(sources),
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    )
    return state


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a real single-agent baseline."""

    _init()
    state = _run_single_agent_baseline(query)
    console.print(Panel.fit(state.final_answer or "", title="Single-Agent Baseline"))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow."""

    _init()
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()
    try:
        result = workflow.run(state)
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc
    console.print(result.model_dump_json(indent=2))


@app.command()
def benchmark(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run baseline and multi-agent benchmark, then write report artifacts."""

    _init()
    baseline_state, baseline_metrics = run_benchmark(
        "single-agent-baseline",
        query,
        _run_single_agent_baseline,
    )
    multi_state, multi_metrics = run_benchmark(
        "multi-agent",
        query,
        lambda item: MultiAgentWorkflow().run(ResearchState(request=ResearchQuery(query=item))),
    )
    report = render_markdown_report([baseline_metrics, multi_metrics])
    store = LocalArtifactStore()
    report_path = store.write_text("benchmark_report.md", report)
    trace_path = store.write_text(
        "benchmark_trace.json",
        json.dumps(
            {
                "baseline": baseline_state.model_dump(mode="json"),
                "multi_agent": multi_state.model_dump(mode="json"),
            },
            indent=2,
            ensure_ascii=False,
        ),
    )

    console.print(Panel.fit(str(report_path), title="Benchmark Report"))
    console.print(Panel.fit(str(trace_path), title="Trace Export"))


if __name__ == "__main__":
    app()
