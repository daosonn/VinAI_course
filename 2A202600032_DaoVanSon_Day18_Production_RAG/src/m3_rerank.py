"""Module 3: reranking with an offline lexical fallback."""

from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RERANK_TOP_K  # noqa: E402


@dataclass
class RerankResult:
    text: str
    original_score: float
    rerank_score: float
    metadata: dict
    rank: int


class CrossEncoderReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", use_model: bool | None = None):
        self.model_name = model_name
        self.use_model = use_model if use_model is not None else os.getenv("LAB18_USE_RERANK_MODEL", "0") == "1"
        self._model = None

    def _load_model(self):
        if not self.use_model:
            return None
        if self._model is None:
            try:
                from FlagEmbedding import FlagReranker

                self._model = ("flag", FlagReranker(self.model_name, use_fp16=True))
            except Exception:
                from sentence_transformers import CrossEncoder

                self._model = ("cross_encoder", CrossEncoder(self.model_name))
        return self._model

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        """Rerank documents and return top-k."""
        if not documents:
            return []

        model = self._load_model()
        if model is not None:
            kind, loaded = model
            pairs = [(query, doc["text"]) for doc in documents]
            scores = loaded.compute_score(pairs) if kind == "flag" else loaded.predict(pairs)
            if not isinstance(scores, list):
                scores = list(scores)
        else:
            scores = [_lexical_relevance(query, doc["text"]) for doc in documents]

        ranked = sorted(zip(scores, documents), key=lambda item: float(item[0]), reverse=True)[:top_k]
        return [
            RerankResult(
                text=doc["text"],
                original_score=float(doc.get("score", 0.0)),
                rerank_score=float(score),
                metadata=doc.get("metadata", {}),
                rank=index + 1,
            )
            for index, (score, doc) in enumerate(ranked)
        ]


class FlashrankReranker:
    """Lightweight alternative with the same fallback scoring contract."""

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        return CrossEncoderReranker(use_model=False).rerank(query, documents, top_k=top_k)


def benchmark_reranker(reranker, query: str, documents: list[dict], n_runs: int = 5) -> dict:
    """Benchmark latency over n_runs."""
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        reranker.rerank(query, documents)
        times.append((time.perf_counter() - start) * 1000)
    return {
        "avg_ms": sum(times) / len(times) if times else 0,
        "min_ms": min(times) if times else 0,
        "max_ms": max(times) if times else 0,
    }


def _lexical_relevance(query: str, text: str) -> float:
    query_tokens = _tokens(query)
    text_tokens = _tokens(text)
    if not query_tokens or not text_tokens:
        return 0.0
    overlap = len(query_tokens & text_tokens)
    number_bonus = len(set(re.findall(r"\d+", query)) & set(re.findall(r"\d+", text))) * 0.5
    phrase_bonus = 2.0 if query.lower() in text.lower() else 0.0
    return overlap + number_bonus + phrase_bonus


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\wÀ-ỹ]+", text.lower(), flags=re.UNICODE))


if __name__ == "__main__":
    query = "Nhân viên được nghỉ phép bao nhiêu ngày?"
    docs = [
        {"text": "Nhân viên được nghỉ 12 ngày/năm.", "score": 0.8, "metadata": {}},
        {"text": "Mật khẩu thay đổi mỗi 90 ngày.", "score": 0.7, "metadata": {}},
    ]
    for result in CrossEncoderReranker().rerank(query, docs):
        print(f"[{result.rank}] {result.rerank_score:.4f} | {result.text}")
