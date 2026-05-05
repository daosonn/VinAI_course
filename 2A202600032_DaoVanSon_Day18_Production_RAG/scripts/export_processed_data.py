"""Export OCR-normalized documents and chunks for manual inspection."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.m1_chunking import chunk_hierarchical, chunk_structure_aware, load_documents  # noqa: E402


def main() -> None:
    base = ROOT / "analysis" / "processed"
    ocr_dir = base / "ocr_markdown"
    structure_dir = base / "structure_chunks"
    hierarchical_dir = base / "hierarchical_chunks"
    for directory in (ocr_dir, structure_dir, hierarchical_dir):
        directory.mkdir(parents=True, exist_ok=True)
        for old_file in directory.glob("*.md"):
            old_file.unlink()

    docs = load_documents()
    manifest = {"ocr_documents": [], "structure_chunks": [], "hierarchical_chunks": []}

    for doc_index, doc in enumerate(docs, start=1):
        text = doc["text"]
        metadata = doc["metadata"]
        name = (
            f"{doc_index:02d}_{_slug(metadata.get('source', 'doc'))}_"
            f"{_slug(metadata.get('section') or metadata.get('article') or metadata.get('doc_type', 'doc'))}.md"
        )
        path = ocr_dir / name
        _write_markdown(path, metadata, text)
        manifest["ocr_documents"].append(_manifest_item(path, metadata, text))

        for chunk_index, chunk in enumerate(chunk_structure_aware(text, metadata=metadata), start=1):
            chunk_path = structure_dir / f"{doc_index:02d}_{chunk_index:02d}_{_slug(metadata.get('source', 'doc'))}.md"
            chunk_metadata = {**chunk.metadata, "chunk_text_chars": len(chunk.text)}
            _write_markdown(chunk_path, chunk_metadata, chunk.text)
            manifest["structure_chunks"].append(_manifest_item(chunk_path, chunk_metadata, chunk.text))

        _, children = chunk_hierarchical(text, metadata=metadata)
        for chunk_index, chunk in enumerate(children, start=1):
            chunk_path = (
                hierarchical_dir
                / f"{doc_index:02d}_{chunk_index:02d}_{_slug(metadata.get('source', 'doc'))}_child.md"
            )
            chunk_metadata = {
                **chunk.metadata,
                "parent_id": chunk.parent_id,
                "chunk_text_chars": len(chunk.text),
            }
            _write_markdown(chunk_path, chunk_metadata, chunk.text)
            manifest["hierarchical_chunks"].append(_manifest_item(chunk_path, chunk_metadata, chunk.text))

    (base / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {len(manifest['ocr_documents'])} OCR docs")
    print(f"Exported {len(manifest['structure_chunks'])} structure chunks")
    print(f"Exported {len(manifest['hierarchical_chunks'])} hierarchical child chunks")
    print(f"Output: {base}")


def _write_markdown(path: Path, metadata: dict, text: str) -> None:
    frontmatter = json.dumps(metadata, ensure_ascii=False, indent=2)
    path.write_text(f"---\nmetadata: {frontmatter}\n---\n\n{text}\n", encoding="utf-8")


def _manifest_item(path: Path, metadata: dict, text: str) -> dict:
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "metadata": metadata,
        "chars": len(text),
    }


def _slug(value: str) -> str:
    return re.sub(r"[^\w.-]+", "_", str(value), flags=re.UNICODE).strip("_")[:80] or "doc"


if __name__ == "__main__":
    main()
