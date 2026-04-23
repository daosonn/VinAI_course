from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM
from .schemas import JudgeResult, QAExample, ReflectionEntry
from .utils import normalize_answer


def _ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.1:8b")


def _ollama_timeout() -> int:
    return int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))


def _extract_json_object(text: str) -> dict:
    text = text.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}


def _chat(messages: list[dict[str, str]], system_instruction: str, expect_json: bool = False) -> tuple[str, int, int]:
    payload = {
        "model": _ollama_model(),
        "stream": False,
        "messages": [{"role": "system", "content": system_instruction}, *messages],
        "options": {"temperature": 0},
    }
    if expect_json:
        payload["format"] = "json"

    request = urllib.request.Request(
        url=f"{_ollama_base_url()}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started_at = time.time()
    try:
        with urllib.request.urlopen(request, timeout=_ollama_timeout()) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        text = "{}" if expect_json else f"Ollama HTTP error {exc.code}: {body}"
        return text, 0, int((time.time() - started_at) * 1000)
    except Exception as exc:
        text = "{}" if expect_json else f"Ollama request failed: {exc}"
        return text, 0, int((time.time() - started_at) * 1000)

    content = raw.get("message", {}).get("content", "").strip()
    prompt_tokens = raw.get("prompt_eval_count", 0) or 0
    completion_tokens = raw.get("eval_count", 0) or 0
    token_count = int(prompt_tokens) + int(completion_tokens)

    total_duration = raw.get("total_duration")
    if total_duration:
        latency_ms = int(total_duration / 1_000_000)
    else:
        latency_ms = int((time.time() - started_at) * 1000)

    return content, token_count, latency_ms


def _format_context(example: QAExample) -> str:
    blocks = []
    for idx, chunk in enumerate(example.context, start=1):
        blocks.append(
            f"[{idx}] Title: {chunk.title}\n"
            f"[{idx}] Evidence: {chunk.text}"
        )
    return "\n\n".join(blocks)


def actor_answer(
    example: QAExample,
    attempt_id: int,
    agent_type: str,
    reflection_memory: list[str],
) -> tuple[str, int, int]:
    prompt_lines = [
        f"Question: {example.question}",
        "Context:",
        _format_context(example),
    ]
    if attempt_id > 1 and reflection_memory and agent_type == "reflexion":
        prompt_lines.extend(
            [
                "",
                "Reflection memory from earlier failed attempts:",
                *[f"- {item}" for item in reflection_memory],
            ]
        )
    prompt_lines.extend(
        [
            "",
            "Give the best final answer based only on the context.",
            'If the context does not support the answer, return "unknown".',
        ]
    )
    response, tokens, latency_ms = _chat(
        messages=[{"role": "user", "content": "\n".join(prompt_lines)}],
        system_instruction=ACTOR_SYSTEM,
        expect_json=False,
    )
    return response.strip(), tokens, latency_ms


def evaluator(example: QAExample, answer: str) -> tuple[JudgeResult, int, int]:
    if normalize_answer(example.gold_answer) == normalize_answer(answer):
        return JudgeResult(score=1, reason="Exact match after normalization."), 0, 0

    prompt = "\n".join(
        [
            f"Question: {example.question}",
            f"Gold answer: {example.gold_answer}",
            f"Model answer: {answer}",
            "",
            "Decide whether the model answer is correct.",
        ]
    )
    response, tokens, latency_ms = _chat(
        messages=[{"role": "user", "content": prompt}],
        system_instruction=EVALUATOR_SYSTEM,
        expect_json=True,
    )
    data = _extract_json_object(response)
    score = int(data.get("score", 0) or 0)
    reason = str(data.get("reason", "Evaluator returned invalid JSON."))
    return JudgeResult(score=1 if score == 1 else 0, reason=reason), tokens, latency_ms


def reflector(
    example: QAExample,
    attempt_id: int,
    answer: str,
    judge: JudgeResult,
) -> tuple[ReflectionEntry, int, int]:
    prompt = "\n".join(
        [
            f"Question: {example.question}",
            "Context:",
            _format_context(example),
            "",
            f"Incorrect answer from attempt {attempt_id}: {answer}",
            f"Evaluator feedback: {judge.reason}",
        ]
    )
    response, tokens, latency_ms = _chat(
        messages=[{"role": "user", "content": prompt}],
        system_instruction=REFLECTOR_SYSTEM,
        expect_json=True,
    )
    data = _extract_json_object(response)
    entry = ReflectionEntry(
        attempt_id=attempt_id,
        failure_reason=str(data.get("failure_reason", judge.reason)),
        lesson=str(data.get("lesson", "Use all context and verify the final entity.")),
        next_strategy=str(
            data.get(
                "next_strategy",
                "Re-read the evidence, complete every hop, and verify the final answer before responding.",
            )
        ),
    )
    return entry, tokens, latency_ms
