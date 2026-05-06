"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Small OpenAI-backed LLM client used by all agents."""

    def __init__(self, model: str | None = None) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise AgentExecutionError("OPENAI_API_KEY is required to use the real LLM client.")

        self.model = model or settings.openai_model
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.timeout_seconds,
        )

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion using OpenAI Chat Completions."""

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        message = completion.choices[0].message.content or ""
        usage = completion.usage
        return LLMResponse(
            content=message.strip(),
            input_tokens=None if usage is None else usage.prompt_tokens,
            output_tokens=None if usage is None else usage.completion_tokens,
        )
