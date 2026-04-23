from __future__ import annotations

from .schemas import JudgeResult, QAExample, ReflectionEntry
from .utils import normalize_answer

FIRST_ATTEMPT_WRONG = {
    "hp2": "London",
    "hp4": "Atlantic Ocean",
    "hp6": "Red Sea",
    "hp8": "Andes",
}


def actor_answer(
    example: QAExample,
    attempt_id: int,
    agent_type: str,
    reflection_memory: list[str],
) -> tuple[str, int, int]:
    if example.qid not in FIRST_ATTEMPT_WRONG:
        return example.gold_answer, 0, 0
    if agent_type == "react":
        return FIRST_ATTEMPT_WRONG[example.qid], 0, 0
    if attempt_id == 1 and not reflection_memory:
        return FIRST_ATTEMPT_WRONG[example.qid], 0, 0
    return example.gold_answer, 0, 0


def evaluator(example: QAExample, answer: str) -> tuple[JudgeResult, int, int]:
    if normalize_answer(example.gold_answer) == normalize_answer(answer):
        return JudgeResult(
            score=1,
            reason="Final answer matches the gold answer after normalization.",
        ), 0, 0
    if normalize_answer(answer) == "london":
        return JudgeResult(
            score=0,
            reason="The answer stopped at the first hop and never completed the river lookup.",
        ), 0, 0
    return JudgeResult(
        score=0,
        reason="The final answer selected the wrong second-hop entity.",
    ), 0, 0


def reflector(
    example: QAExample,
    attempt_id: int,
    answer: str,
    judge: JudgeResult,
) -> tuple[ReflectionEntry, int, int]:
    strategy = (
        "Do the second hop explicitly: birthplace city to river through that city."
        if example.qid == "hp2"
        else "Verify the final entity against the second context paragraph before answering."
    )
    return ReflectionEntry(
        attempt_id=attempt_id,
        failure_reason=judge.reason,
        lesson="A partial first-hop answer is not enough; the final answer must complete all hops.",
        next_strategy=strategy,
    ), 0, 0
