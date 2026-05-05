"""Module 5: offline-first enrichment pipeline for chunks before embedding."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY  # noqa: E402


@dataclass
class EnrichedChunk:
    """Chunk enriched for retrieval."""

    original_text: str
    enriched_text: str
    summary: str
    hypothesis_questions: list[str]
    auto_metadata: dict
    method: str


def summarize_chunk(text: str) -> str:
    """Create a short summary, using OpenAI only when explicitly configured."""
    if _use_openai():
        try:
            from openai import OpenAI

            client = OpenAI()
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Tóm tắt đoạn văn sau trong 2 câu ngắn bằng tiếng Việt.",
                    },
                    {"role": "user", "content": text},
                ],
                max_tokens=150,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            print(f"[m5_enrichment] OpenAI summary fallback: {exc}")

    sentences = _sentences(text)
    return " ".join(sentences[:2]).strip()


def generate_hypothesis_questions(text: str, n_questions: int = 3) -> list[str]:
    """Generate likely Vietnamese questions that this chunk can answer."""
    if _use_openai():
        try:
            from openai import OpenAI

            client = OpenAI()
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"Tạo {n_questions} câu hỏi mà đoạn văn có thể trả lời. Mỗi câu một dòng.",
                    },
                    {"role": "user", "content": text},
                ],
                max_tokens=200,
            )
            return _clean_questions(resp.choices[0].message.content.splitlines())[:n_questions]
        except Exception as exc:
            print(f"[m5_enrichment] OpenAI HyQA fallback: {exc}")

    metadata = extract_metadata(text)
    topic = metadata.get("topic") or _first_keywords(text)
    questions = [
        f"{topic} là gì?",
        f"{topic} được quy định như thế nào?",
        f"Thông tin quan trọng về {topic} là gì?",
    ]
    return questions[:n_questions]


def contextual_prepend(text: str, document_title: str = "") -> str:
    """Prepend a short retrieval context while preserving the original text."""
    title = document_title or "tài liệu nguồn"
    metadata = extract_metadata(text)
    topic = metadata.get("topic") or "nội dung liên quan"
    context = f"Đoạn này trích từ {title} và nói về {topic}."
    return f"{context}\n\n{text}"


def extract_metadata(text: str) -> dict:
    """Extract lightweight metadata for Vietnamese legal/tax documents."""
    lowered = text.lower()
    if "thuế gtgt" in lowered or "giá trị gia tăng" in lowered or "[43]" in text:
        category = "tax"
        topic = "thuế giá trị gia tăng"
    elif "dữ liệu cá nhân" in lowered or "nghị định" in lowered:
        category = "policy"
        topic = "bảo vệ dữ liệu cá nhân"
    else:
        category = "general"
        topic = _first_keywords(text)

    entities = []
    for pattern in [
        r"CÔNG TY[^\n|.]+",
        r"Nghị định\s+\d+/?\d*",
        r"\[\d+[a-z]?\]",
    ]:
        entities.extend(match.group(0).strip() for match in re.finditer(pattern, text, flags=re.IGNORECASE))

    return {
        "topic": topic,
        "entities": sorted(set(entities))[:10],
        "category": category,
        "language": "vi",
    }


def enrich_chunks(
    chunks: list[dict],
    methods: list[str] | None = None,
) -> list[EnrichedChunk]:
    """Run selected enrichment methods on chunks."""
    if methods is None:
        methods = ["contextual", "hyqa", "metadata"]

    apply_all = "full" in methods
    enriched: list[EnrichedChunk] = []
    for chunk in chunks:
        text = chunk["text"]
        metadata = chunk.get("metadata", {})
        summary = summarize_chunk(text) if apply_all or "summary" in methods else ""
        questions = generate_hypothesis_questions(text) if apply_all or "hyqa" in methods else []
        enriched_text = (
            contextual_prepend(text, metadata.get("source", ""))
            if apply_all or "contextual" in methods
            else text
        )
        auto_meta = extract_metadata(text) if apply_all or "metadata" in methods else {}
        enriched.append(
            EnrichedChunk(
                original_text=text,
                enriched_text=enriched_text,
                summary=summary,
                hypothesis_questions=questions,
                auto_metadata={**metadata, **auto_meta},
                method="+".join(methods),
            )
        )
    return enriched


def _use_openai() -> bool:
    return bool(OPENAI_API_KEY) and os.getenv("LAB18_USE_OPENAI_ENRICHMENT", "0") == "1"


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def _clean_questions(lines: list[str]) -> list[str]:
    questions = []
    for line in lines:
        question = line.strip().lstrip("-0123456789.) ")
        if question:
            questions.append(question)
    return questions


def _first_keywords(text: str) -> str:
    words = re.findall(r"[\wÀ-ỹ]+", text.lower(), flags=re.UNICODE)
    stopwords = {"và", "là", "của", "trong", "được", "với", "cho", "các", "một", "này"}
    keywords = [word for word in words if len(word) > 3 and word not in stopwords]
    return " ".join(keywords[:4]) if keywords else "nội dung tài liệu"


if __name__ == "__main__":
    sample = "Nhân viên chính thức được nghỉ phép năm 12 ngày làm việc mỗi năm."
    print(json.dumps(extract_metadata(sample), ensure_ascii=False, indent=2))
