"""Critic agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class CriticAgent(BaseAgent):
    """Fact-checking and quality-review agent."""

    name = "critic"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final answer and append findings."""

        if not state.final_answer:
            message = "Critic skipped: no final answer was available."
            state.errors.append(message)
            return state

        source_lines = "\n".join(
            f"[{index}] {source.title}: {source.snippet}"
            for index, source in enumerate(state.sources, start=1)
        )
        response = self.llm_client.complete(
            system_prompt=(
                "You are a strict critic for a research assistant. Review the final "
                "answer against the available sources. Do not add new facts. Focus on "
                "citation coverage, hallucination risk, missing caveats, and clarity."
            ),
            user_prompt=(
                f"Original query: {state.request.query}\n\n"
                f"Sources:\n{source_lines or 'No sources available.'}\n\n"
                f"Final answer:\n{state.final_answer}\n\n"
                "Return a concise review with:\n"
                "- Verdict: PASS or NEEDS_REVISION\n"
                "- Quality score: 0-10\n"
                "- Citation coverage\n"
                "- Main risks\n"
                "- One concrete improvement"
            ),
        )

        state.agent_results.append(
            AgentResult(
                agent=AgentName.CRITIC,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "estimated_cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "agent.critic",
            {
                "has_final_answer": True,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
        return state
