"""Writer agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""

        source_lines = "\n".join(
            f"[{index}] {source.title} - {source.url or 'N/A'}"
            for index, source in enumerate(state.sources, start=1)
        )
        response = self.llm_client.complete(
            system_prompt=(
                "You are the writer in a multi-agent research workflow. Write a clear, "
                "well-structured final answer for the requested audience. Use citation "
                "markers like [1] for sourced claims. Do not invent sources."
            ),
            user_prompt=(
                f"Original query: {state.request.query}\n"
                f"Audience: {state.request.audience}\n\n"
                f"Research notes:\n{state.research_notes or 'N/A'}\n\n"
                f"Analysis notes:\n{state.analysis_notes or 'N/A'}\n\n"
                f"Available sources:\n{source_lines or 'No sources available.'}\n\n"
                "Write the final answer in a beginner-friendly style. Include a short "
                "limitations section if sources are weak or incomplete."
            ),
        )

        final_answer = response.content
        state.final_answer = final_answer
        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=final_answer,
                metadata={
                    "source_count": len(state.sources),
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "estimated_cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "agent.writer",
            {
                "has_final_answer": True,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
        return state
