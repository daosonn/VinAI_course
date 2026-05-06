"""Analyst agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""

        if not state.research_notes:
            message = "Analyst skipped: no research notes were available."
            state.errors.append(message)
            state.analysis_notes = message
            return state

        response = self.llm_client.complete(
            system_prompt=(
                "You are an analyst in a multi-agent research workflow. Transform "
                "research notes into structured insight. Be explicit about trade-offs, "
                "failure modes, and evidence strength."
            ),
            user_prompt=(
                f"Original query: {state.request.query}\n\n"
                f"Research notes:\n{state.research_notes}\n\n"
                "Produce analysis with these sections:\n"
                "1. Main answer direction\n"
                "2. Key comparisons or trade-offs\n"
                "3. Evidence gaps and risks\n"
                "4. Recommended structure for the writer\n"
                "Keep citation markers like [1] when claims depend on sources."
            ),
        )

        notes = response.content
        state.analysis_notes = notes
        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=notes,
                metadata={
                    "source_count": len(state.sources),
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "estimated_cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "agent.analyst",
            {
                "has_research_notes": True,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
        return state
