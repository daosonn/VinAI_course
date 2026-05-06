"""Supervisor / router implementation for the mock lab workflow."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import AgentName
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route."""

        settings = get_settings()
        critic_has_run = any(result.agent == AgentName.CRITIC for result in state.agent_results)

        if state.iteration >= settings.max_iterations:
            route = "done"
            state.errors.append("Supervisor stopped the workflow at max_iterations.")
        elif state.final_answer and critic_has_run:
            route = "done"
        elif state.final_answer:
            route = "critic"
        elif not state.sources or not state.research_notes:
            route = "researcher"
        elif not state.analysis_notes:
            route = "analyst"
        else:
            route = "writer"

        state.record_route(route)
        state.add_trace_event(
            "agent.supervisor",
            {
                "next_route": route,
                "iteration": state.iteration,
                "has_sources": bool(state.sources),
                "has_research_notes": bool(state.research_notes),
                "has_analysis_notes": bool(state.analysis_notes),
                "has_final_answer": bool(state.final_answer),
                "critic_has_run": critic_has_run,
            },
        )
        return state
