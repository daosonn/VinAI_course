"""Researcher agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(
        self,
        search_client: SearchClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.search_client = search_client or SearchClient()
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""

        query = state.request.query
        sources = self.search_client.search(query, max_results=state.request.max_sources)
        source_context = "\n".join(
            f"[{index}] {source.title}\nURL: {source.url or 'N/A'}\nSnippet: {source.snippet}"
            for index, source in enumerate(sources, start=1)
        )
        response = self.llm_client.complete(
            system_prompt=(
                "You are a careful research assistant. Create compact research notes "
                "from the provided sources only. Preserve citation numbers like [1]. "
                "If evidence is weak, say so clearly."
            ),
            user_prompt=(
                f"Research query: {query}\n\n"
                f"Audience: {state.request.audience}\n\n"
                f"Sources:\n{source_context}\n\n"
                "Write concise research notes with: key facts, useful citations, "
                "uncertainties, and what the analyst should compare."
            ),
        )

        notes = response.content
        state.sources = sources
        state.research_notes = notes
        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=notes,
                metadata={
                    "source_count": len(sources),
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "estimated_cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "agent.researcher",
            {
                "source_count": len(sources),
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
        return state
