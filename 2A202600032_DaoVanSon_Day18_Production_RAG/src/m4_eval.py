"""Module 4: RAGAS evaluation with offline fallback metrics."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH  # noqa: E402


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
) -> dict:
    """Run RAGAS if explicitly enabled, otherwise use deterministic fallback scores."""
    if os.getenv("LAB18_USE_RAGAS", "0") == "1":
        try:
            from datasets import Dataset
            from ragas import evaluate
            from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

            dataset = Dataset.from_dict(
                {
                    "question": questions,
                    "answer": answers,
                    "contexts": contexts,
                    "ground_truth": ground_truths,
                }
            )
            result = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            )
            df = result.to_pandas()
            per_question = [
                EvalResult(
                    question=row["question"],
                    answer=row["answer"],
                    contexts=row["contexts"],
                    ground_truth=row["ground_truth"],
                    faithfulness=float(row["faithfulness"]),
                    answer_relevancy=float(row["answer_relevancy"]),
                    context_precision=float(row["context_precision"]),
                    context_recall=float(row["context_recall"]),
                )
                for _, row in df.iterrows()
            ]
            return _aggregate(per_question)
        except Exception as exc:
            print(f"[m4_eval] RAGAS failed, using fallback metrics: {exc}")

    per_question = [
        _score_one(question, answer, context, ground_truth)
        for question, answer, context, ground_truth in zip(questions, answers, contexts, ground_truths)
    ]
    return _aggregate(per_question)


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using a simple diagnostic tree."""
    ranked = sorted(eval_results, key=_average_score)[:bottom_n]
    failures = []
    for result in ranked:
        metrics = {
            "faithfulness": result.faithfulness,
            "answer_relevancy": result.answer_relevancy,
            "context_precision": result.context_precision,
            "context_recall": result.context_recall,
        }
        worst_metric = min(metrics, key=metrics.get)
        diagnosis, suggested_fix = _diagnose(worst_metric, metrics[worst_metric])
        failures.append(
            {
                "question": result.question,
                "worst_metric": worst_metric,
                "score": float(metrics[worst_metric]),
                "diagnosis": diagnosis,
                "suggested_fix": suggested_fix,
            }
        )
    return failures


def save_report(results: dict, failures: list[dict], path: str = "ragas_report.json"):
    """Save evaluation report to JSON."""
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=_json_default)
    print(f"Report saved to {path}")


def _score_one(question: str, answer: str, contexts: list[str], ground_truth: str) -> EvalResult:
    context_text = "\n".join(contexts)
    faithfulness = _overlap_score(answer, context_text)
    answer_relevancy = max(_overlap_score(question, answer), _overlap_score(ground_truth, answer))
    context_precision = _overlap_score(question, context_text)
    context_recall = _overlap_score(ground_truth, context_text)
    return EvalResult(
        question=question,
        answer=answer,
        contexts=contexts,
        ground_truth=ground_truth,
        faithfulness=faithfulness,
        answer_relevancy=answer_relevancy,
        context_precision=context_precision,
        context_recall=context_recall,
    )


def _aggregate(per_question: list[EvalResult]) -> dict:
    metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    aggregate = {
        metric: (
            sum(float(getattr(result, metric)) for result in per_question) / len(per_question)
            if per_question
            else 0.0
        )
        for metric in metrics
    }
    aggregate["per_question"] = per_question
    return aggregate


def _overlap_score(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return min(1.0, len(left_tokens & right_tokens) / len(left_tokens))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\wÀ-ỹ]+", text.lower(), flags=re.UNICODE))


def _average_score(result: EvalResult) -> float:
    return (result.faithfulness + result.answer_relevancy + result.context_precision + result.context_recall) / 4


def _diagnose(metric: str, score: float) -> tuple[str, str]:
    if metric == "faithfulness" and score < 0.85:
        return "LLM hallucinating", "Tighten prompt, cite context, lower temperature"
    if metric == "context_recall" and score < 0.75:
        return "Missing relevant chunks", "Improve OCR, chunking, or hybrid search"
    if metric == "context_precision" and score < 0.75:
        return "Too many irrelevant chunks", "Add reranking or metadata filters"
    if metric == "answer_relevancy" and score < 0.80:
        return "Answer mismatch", "Improve prompt template and answer extraction"
    return "Low aggregate score", "Inspect retrieval context and generation prompt"


def _json_default(value):
    if isinstance(value, EvalResult):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
