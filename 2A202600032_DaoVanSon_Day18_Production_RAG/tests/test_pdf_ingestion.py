import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.pdf_ingestion import ingest_pdf
from src.m1_chunking import load_documents
from src.m2_search import BM25Search


def test_bctc_table_continuation_chunk():
    docs = ingest_pdf("data/BCTC.pdf", run_ocr=False)
    table_docs = [doc for doc in docs if doc.metadata.get("table_id") == "vat_declaration_main_table"]
    assert table_docs, "BCTC should expose one merged VAT table chunk"

    table = table_docs[0]
    assert table.metadata["page_start"] == 1
    assert table.metadata["page_end"] == 2
    assert table.metadata["continued_across_pages"] is True
    for code in ["[40]", "[41]", "[42]", "[43]"]:
        assert code in table.text


def test_bctc_signature_separate_from_table():
    docs = ingest_pdf("data/BCTC.pdf", run_ocr=False)
    assert any(doc.metadata.get("section") == "signature" for doc in docs)
    table_text = next(doc.text for doc in docs if doc.metadata.get("table_id") == "vat_declaration_main_table")
    assert "Tôi cam đoan" not in table_text


def test_legal_seed_contains_article_2():
    docs = ingest_pdf("data/Nghi_dinh_so_13-2023_ve_bao_ve_du_lieu_ca_nhan_508ee.pdf", run_ocr=False)
    assert any("Điều 2. Giải thích từ ngữ" in doc.text for doc in docs)
    assert any(doc.metadata.get("article") == "Điều 2" for doc in docs)


def test_search_retrieves_bctc_continued_row():
    docs = load_documents()
    search = BM25Search()
    search.index(docs)
    results = search.search("Thuế GTGT còn được khấu trừ chuyển kỳ sau là bao nhiêu?", top_k=3)
    assert results
    assert any("[43]" in result.text for result in results)


def test_search_retrieves_legal_article_2():
    docs = load_documents()
    search = BM25Search()
    search.index(docs)
    results = search.search("Dữ liệu cá nhân là gì?", top_k=3)
    assert results
    assert any("Điều 2" in result.text for result in results)
