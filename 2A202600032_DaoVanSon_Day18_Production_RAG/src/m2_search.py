"""Module 2: Hybrid Search - Vietnamese BM25 + dense fallback + RRF."""

from __future__ import annotations

import math
import os
import re
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (  # noqa: E402
    BM25_TOP_K,
    COLLECTION_NAME,
    DENSE_TOP_K,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    HYBRID_TOP_K,
    QDRANT_HOST,
    QDRANT_PORT,
)


@dataclass
class SearchResult:
    text: str
    score: float
    metadata: dict
    method: str


def segment_vietnamese(text: str) -> str:
    """Segment Vietnamese text for sparse retrieval."""
    try:
        from underthesea import word_tokenize

        return word_tokenize(text, format="text")
    except Exception:
        return " ".join(re.findall(r"[\wÀ-ỹ]+|\[\d+[a-z]?\]", text, flags=re.UNICODE))


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in segment_vietnamese(text).split() if token.strip()]


def _lexical_score(query: str, document: str) -> float:
    query_tokens = _tokens(query)
    doc_tokens = _tokens(document)
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_counts: dict[str, int] = {}
    for token in doc_tokens:
        doc_counts[token] = doc_counts.get(token, 0) + 1
    overlap = sum(doc_counts.get(token, 0) for token in query_tokens)
    phrase_bonus = 2.0 if query.lower() in document.lower() else 0.0
    return overlap / math.sqrt(len(doc_tokens)) + phrase_bonus


class BM25Search:
    def __init__(self):
        self.corpus_tokens: list[list[str]] = []
        self.documents: list[dict] = []
        self.bm25 = None

    def index(self, chunks: list[dict]) -> None:
        """Build BM25 index from chunks."""
        self.documents = chunks
        self.corpus_tokens = [_tokens(chunk["text"]) for chunk in chunks]
        if not self.corpus_tokens:
            self.bm25 = None
            return
        from rank_bm25 import BM25Okapi

        self.bm25 = BM25Okapi(self.corpus_tokens)

    def search(self, query: str, top_k: int = BM25_TOP_K) -> list[SearchResult]:
        """Search using BM25."""
        if not self.documents:
            return []
        tokenized_query = _tokens(query)
        if self.bm25 is None:
            scores = [_lexical_score(query, doc["text"]) for doc in self.documents]
        else:
            scores = list(self.bm25.get_scores(tokenized_query))
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            SearchResult(
                text=self.documents[i]["text"],
                score=float(scores[i]),
                metadata=self.documents[i].get("metadata", {}),
                method="bm25",
            )
            for i in top_indices
            if scores[i] > 0 or top_k >= len(self.documents)
        ]


class DenseSearch:
    """Dense search with Qdrant when available, lexical fallback otherwise."""

    def __init__(self):
        self._encoder = None
        self._client = None
        self._fallback_documents: list[dict] = []
        try:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=3)
        except Exception:
            self._client = None

    def _get_encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer

            self._encoder = SentenceTransformer(EMBEDDING_MODEL)
        return self._encoder

    def index(self, chunks: list[dict], collection: str = COLLECTION_NAME) -> None:
        """Index chunks into Qdrant, or keep an in-memory fallback."""
        self._fallback_documents = chunks
        if not chunks or self._client is None:
            return
        try:
            from qdrant_client.models import Distance, PointStruct, VectorParams

            self._client.recreate_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )
            texts = [chunk["text"] for chunk in chunks]
            vectors = self._get_encoder().encode(texts, show_progress_bar=False)
            points = [
                PointStruct(
                    id=index,
                    vector=vector.tolist(),
                    payload={**chunk.get("metadata", {}), "text": chunk["text"]},
                )
                for index, (chunk, vector) in enumerate(zip(chunks, vectors))
            ]
            self._client.upsert(collection_name=collection, points=points)
        except Exception as exc:
            print(f"[DenseSearch] Falling back to lexical dense stub: {exc}")
            self._client = None

    def search(
        self,
        query: str,
        top_k: int = DENSE_TOP_K,
        collection: str = COLLECTION_NAME,
    ) -> list[SearchResult]:
        """Search using dense vectors or a lexical fallback."""
        if self._client is not None:
            try:
                query_vector = self._get_encoder().encode(query).tolist()
                hits = self._client.search(collection_name=collection, query_vector=query_vector, limit=top_k)
                return [
                    SearchResult(
                        text=hit.payload.get("text", ""),
                        score=float(hit.score),
                        metadata={k: v for k, v in hit.payload.items() if k != "text"},
                        method="dense",
                    )
                    for hit in hits
                ]
            except Exception as exc:
                print(f"[DenseSearch] Query fallback: {exc}")
                self._client = None

        scored = [
            (_lexical_score(query, chunk["text"]), chunk)
            for chunk in self._fallback_documents
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            SearchResult(
                text=chunk["text"],
                score=float(score),
                metadata=chunk.get("metadata", {}),
                method="dense",
            )
            for score, chunk in scored[:top_k]
            if score > 0
        ]


def reciprocal_rank_fusion(
    results_list: list[list[SearchResult]],
    k: int = 60,
    top_k: int = HYBRID_TOP_K,
) -> list[SearchResult]:
    """Merge ranked lists using RRF: score(d) = sum(1 / (k + rank))."""
    fused: dict[str, dict] = {}
    for result_list in results_list:
        for rank, result in enumerate(result_list, start=1):
            item = fused.setdefault(result.text, {"score": 0.0, "result": result})
            item["score"] += 1.0 / (k + rank)

    ranked = sorted(fused.values(), key=lambda item: item["score"], reverse=True)[:top_k]
    return [
        SearchResult(
            text=item["result"].text,
            score=float(item["score"]),
            metadata=item["result"].metadata,
            method="hybrid",
        )
        for item in ranked
    ]


class HybridSearch:
    """Combines BM25 + dense/fallback + RRF."""

    def __init__(self):
        self.bm25 = BM25Search()
        self.dense = DenseSearch()

    def index(self, chunks: list[dict]) -> None:
        self.bm25.index(chunks)
        self.dense.index(chunks)

    def search(self, query: str, top_k: int = HYBRID_TOP_K) -> list[SearchResult]:
        bm25_results = self.bm25.search(query, top_k=BM25_TOP_K)
        dense_results = self.dense.search(query, top_k=DENSE_TOP_K)
        return reciprocal_rank_fusion([bm25_results, dense_results], top_k=top_k)


if __name__ == "__main__":
    sample = "Nhân viên được nghỉ phép năm"
    print(f"Original:  {sample}")
    print(f"Segmented: {segment_vietnamese(sample)}")
