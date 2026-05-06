from multi_agent_research_lab.agents import SupervisorAgent
from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import (
    AgentName,
    AgentResult,
    ResearchQuery,
    SourceDocument,
)
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


class FakeAgent(BaseAgent):
    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, state: ResearchState) -> ResearchState:
        if self.name == "researcher":
            state.sources = [
                SourceDocument(
                    title="Fake source",
                    url="https://example.com",
                    snippet="Fake snippet",
                )
            ]
            state.research_notes = "Fake research notes [1]."
        elif self.name == "analyst":
            state.analysis_notes = "Fake analysis notes."
        elif self.name == "writer":
            state.final_answer = "Fake final answer [1]."
        elif self.name == "critic":
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.CRITIC,
                    content="Verdict: PASS\nQuality score: 8",
                )
            )
        return state


def test_supervisor_routes_by_missing_state_fields() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))

    SupervisorAgent().run(state)
    assert state.route_history[-1] == "researcher"

    state.sources = [
        SourceDocument(
            title="Mock source",
            url="https://example.com",
            snippet="Mock snippet",
        )
    ]
    state.research_notes = "Mock research notes"
    SupervisorAgent().run(state)
    assert state.route_history[-1] == "analyst"

    state.analysis_notes = "Mock analysis"
    SupervisorAgent().run(state)
    assert state.route_history[-1] == "writer"

    state.final_answer = "Mock final answer"
    SupervisorAgent().run(state)
    assert state.route_history[-1] == "critic"

    state.agent_results.append(AgentResult(agent=AgentName.CRITIC, content="Verdict: PASS"))
    SupervisorAgent().run(state)
    assert state.route_history[-1] == "done"


def test_mock_workflow_runs_end_to_end_without_api_calls() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    agents = {
        "researcher": FakeAgent("researcher"),
        "analyst": FakeAgent("analyst"),
        "writer": FakeAgent("writer"),
        "critic": FakeAgent("critic"),
    }

    result = MultiAgentWorkflow(agents=agents).run(state)

    assert result.route_history == ["researcher", "analyst", "writer", "critic", "done"]
    assert result.sources
    assert result.research_notes
    assert result.analysis_notes
    assert result.final_answer
    assert any(item.agent == AgentName.CRITIC for item in result.agent_results)
