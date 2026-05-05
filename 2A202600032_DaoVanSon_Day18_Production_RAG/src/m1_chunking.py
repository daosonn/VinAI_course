"""Module 1: advanced chunking strategies for Vietnamese RAG data."""

from __future__ import annotations

import glob
import os
import re
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (  # noqa: E402
    DATA_DIR,
    HIERARCHICAL_CHILD_SIZE,
    HIERARCHICAL_PARENT_SIZE,
    SEMANTIC_THRESHOLD,
)
from src.pdf_ingestion import load_pdf_documents  # noqa: E402


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)
    parent_id: str | None = None


def load_documents(data_dir: str = DATA_DIR) -> list[dict]:
    """Load Markdown/text files and structured scan-PDF documents from data/."""
    docs: list[dict] = []
    for pattern in ("*.md", "*.txt"):
        for fp in sorted(glob.glob(os.path.join(data_dir, pattern))):
            with open(fp, encoding="utf-8") as f:
                docs.append({"text": f.read(), "metadata": {"source": os.path.basename(fp)}})
    docs.extend(load_pdf_documents(data_dir))
    return [doc for doc in docs if doc.get("text", "").strip()]


def chunk_basic(text: str, chunk_size: int = 500, metadata: dict | None = None) -> list[Chunk]:
    """Baseline paragraph chunking."""
    metadata = metadata or {}
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[Chunk] = []
    current = ""
    for para in paragraphs:
        separator = "\n\n" if current else ""
        if len(current) + len(separator) + len(para) > chunk_size and current:
            chunks.append(Chunk(text=current.strip(), metadata={**metadata, "chunk_index": len(chunks)}))
            current = ""
            separator = ""
        current = f"{current}{separator}{para}"
    if current.strip():
        chunks.append(Chunk(text=current.strip(), metadata={**metadata, "chunk_index": len(chunks)}))
    return chunks


def chunk_semantic(
    text: str,
    threshold: float = SEMANTIC_THRESHOLD,
    metadata: dict | None = None,
) -> list[Chunk]:
    """Group neighboring sentences/sections by lightweight lexical similarity.

    The production path can swap this for embedding-based similarity, but this
    deterministic version is fast, offline, and Vietnamese-friendly enough for
    tests and small scan-OCR corpora.
    """
    metadata = metadata or {}
    sentences = _split_sentences(text)
    if not sentences:
        return []

    groups: list[list[str]] = [[sentences[0]]]
    for sentence in sentences[1:]:
        previous = groups[-1][-1]
        starts_section = bool(re.match(r"^#{1,6}\s+", sentence))
        similarity = _jaccard_similarity(previous, sentence)
        current_size = len("\n".join(groups[-1]))
        if starts_section or (similarity < threshold and current_size > 250):
            groups.append([sentence])
        else:
            groups[-1].append(sentence)

    return [
        Chunk(
            text="\n".join(group).strip(),
            metadata={**metadata, "chunk_index": index, "strategy": "semantic"},
        )
        for index, group in enumerate(groups)
        if "\n".join(group).strip()
    ]


def chunk_hierarchical(
    text: str,
    parent_size: int = HIERARCHICAL_PARENT_SIZE,
    child_size: int = HIERARCHICAL_CHILD_SIZE,
    metadata: dict | None = None,
) -> tuple[list[Chunk], list[Chunk]]:
    """Create parent chunks for context and child chunks for retrieval."""
    metadata = metadata or {}
    parent_texts = _split_by_size(text, parent_size)
    parents: list[Chunk] = []
    children: list[Chunk] = []
    source_slug = re.sub(r"\W+", "_", str(metadata.get("source", "doc"))).strip("_") or "doc"

    for parent_index, parent_text in enumerate(parent_texts):
        parent_id = f"{source_slug}_parent_{parent_index}"
        parents.append(
            Chunk(
                text=parent_text,
                metadata={
                    **metadata,
                    "chunk_type": "parent",
                    "chunk_index": parent_index,
                    "parent_id": parent_id,
                    "strategy": "hierarchical",
                },
            )
        )
        for child_index, child_text in enumerate(_split_by_size(parent_text, child_size)):
            children.append(
                Chunk(
                    text=child_text,
                    metadata={
                        **metadata,
                        "chunk_type": "child",
                        "chunk_index": child_index,
                        "parent_index": parent_index,
                        "strategy": "hierarchical",
                    },
                    parent_id=parent_id,
                )
            )
    return parents, children


def chunk_structure_aware(text: str, metadata: dict | None = None) -> list[Chunk]:
    """Chunk Markdown by headers while preserving whole tables and lists."""
    metadata = metadata or {}
    chunks: list[Chunk] = []
    current_header = ""
    current_lines: list[str] = []

    def flush() -> None:
        if not any(line.strip() for line in current_lines):
            return
        section_text = "\n".join(([current_header] if current_header else []) + current_lines).strip()
        if not section_text:
            return
        chunks.append(
            Chunk(
                text=section_text,
                metadata={
                    **metadata,
                    "section": current_header.strip("# ").strip() if current_header else "",
                    "chunk_index": len(chunks),
                    "strategy": "structure",
                },
            )
        )

    for line in text.splitlines():
        if re.match(r"^#{1,6}\s+", line):
            flush()
            current_header = line.strip()
            current_lines = []
        else:
            current_lines.append(line.rstrip())
    flush()
    return chunks or chunk_basic(text, metadata={**metadata, "strategy": "structure"})


def compare_strategies(documents: list[dict]) -> dict:
    """Run all strategies on documents and return comparison stats."""
    basic: list[Chunk] = []
    semantic: list[Chunk] = []
    parents: list[Chunk] = []
    children: list[Chunk] = []
    structure: list[Chunk] = []

    for doc in documents:
        text = doc.get("text", "")
        metadata = doc.get("metadata", {})
        basic.extend(chunk_basic(text, metadata=metadata))
        semantic.extend(chunk_semantic(text, metadata=metadata))
        doc_parents, doc_children = chunk_hierarchical(text, metadata=metadata)
        parents.extend(doc_parents)
        children.extend(doc_children)
        structure.extend(chunk_structure_aware(text, metadata=metadata))

    results = {
        "basic": _stats(basic),
        "semantic": _stats(semantic),
        "hierarchical": {
            **_stats(children),
            "num_parents": len(parents),
            "num_children": len(children),
        },
        "structure": _stats(structure),
    }

    print(f"{'Strategy':<14} | {'Chunks':>8} | {'Avg Len':>8} | {'Min':>5} | {'Max':>5}")
    print("-" * 52)
    for name, stats in results.items():
        label = (
            f"{stats.get('num_parents', 0)}p/{stats.get('num_children', 0)}c"
            if name == "hierarchical"
            else str(stats["num_chunks"])
        )
        print(
            f"{name:<14} | {label:>8} | {stats['avg_length']:>8} | "
            f"{stats['min_length']:>5} | {stats['max_length']:>5}"
        )
    return results


def _split_sentences(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sentences: list[str] = []
    for line in lines:
        if line.startswith("|") or re.match(r"^#{1,6}\s+", line):
            sentences.append(line)
            continue
        parts = re.split(r"(?<=[.!?])\s+|(?<=;)\s+", line)
        sentences.extend(part.strip() for part in parts if part.strip())
    return sentences


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[\wÀ-ỹ]+", text.lower(), flags=re.UNICODE))


def _jaccard_similarity(a: str, b: str) -> float:
    left, right = _tokenize(a), _tokenize(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _split_by_size(text: str, max_size: int) -> list[str]:
    paragraphs = _markdown_blocks(text)

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if _is_markdown_table(para):
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.append(para.strip())
            continue

        separator = "\n\n" if current else ""
        if current and len(current) + len(separator) + len(para) > max_size:
            chunks.append(current.strip())
            current = ""
            separator = ""
        if len(para) <= max_size:
            current = f"{current}{separator}{para}".strip()
            continue

        words = para.split()
        buffer = ""
        for word in words:
            if buffer and len(buffer) + 1 + len(word) > max_size:
                chunks.append(buffer.strip())
                buffer = word
            else:
                buffer = f"{buffer} {word}".strip()
        current = buffer

    if current:
        chunks.append(current.strip())
    return chunks


def _markdown_blocks(text: str) -> list[str]:
    """Split Markdown into paragraphs while keeping tables indivisible."""
    lines = text.splitlines()
    blocks: list[str] = []
    current: list[str] = []
    in_table = False

    def flush() -> None:
        nonlocal current
        block = "\n".join(current).strip()
        if block:
            blocks.append(block)
        current = []

    for line in lines:
        is_table_line = line.strip().startswith("|")
        if is_table_line:
            if current and not in_table:
                flush()
            in_table = True
            current.append(line.rstrip())
            continue
        if in_table:
            flush()
            in_table = False
        if line.strip():
            current.append(line.rstrip())
        else:
            flush()
    flush()
    return blocks


def _is_markdown_table(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    return len(lines) >= 2 and all(line.strip().startswith("|") for line in lines[:2])


def _stats(chunks: list[Chunk]) -> dict:
    lengths = [len(chunk.text) for chunk in chunks]
    return {
        "num_chunks": len(chunks),
        "avg_length": round(sum(lengths) / len(lengths), 1) if lengths else 0,
        "min_length": min(lengths) if lengths else 0,
        "max_length": max(lengths) if lengths else 0,
    }


if __name__ == "__main__":
    docs = load_documents()
    print(f"Loaded {len(docs)} documents")
    results = compare_strategies(docs)
    for name, stats in results.items():
        print(f"  {name}: {stats}")
