"""Simple mock workflow for the multi-agent lab."""

from multi_agent_research_lab.agents import (
    AnalystAgent,
    CriticAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    The lab implementation uses a small Python loop instead of a real LangGraph
    graph so learners can inspect the routing logic before adding frameworks.
    """

    def __init__(
        self,
        supervisor: SupervisorAgent | None = None,
        agents: dict[str, BaseAgent] | None = None,
    ) -> None:
        self.supervisor = supervisor or SupervisorAgent()
        self.agents = agents or self.build()

    def build(self) -> dict[str, BaseAgent]:
        """Create the worker registry used by the workflow."""

        return {
            "researcher": ResearcherAgent(),
            "analyst": AnalystAgent(),
            "writer": WriterAgent(),
            "critic": CriticAgent(),
        }

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the mock graph and return final state."""

        while True:
            with trace_span("workflow.supervisor") as span:
                state = self.supervisor.run(state)
            state.add_trace_event("span.workflow.supervisor", span)

            route = state.route_history[-1]
            if route == "done":
                return state

            agent = self.agents.get(route)
            if agent is None:
                raise AgentExecutionError(f"Unknown route from supervisor: {route}")

            with trace_span(f"workflow.{route}") as span:
                state = agent.run(state)
            state.add_trace_event(f"span.workflow.{route}", span)
