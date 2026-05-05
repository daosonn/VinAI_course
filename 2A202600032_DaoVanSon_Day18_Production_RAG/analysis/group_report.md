# Group Report - Lab 18: Production RAG

**Nhóm:** Đào Văn Sơn  
**Hình thức:** Làm cá nhân  
**Ngày:** 05/05/2026

## Thành viên & Phân công

| Tên | Module | Hoàn thành | Tests pass |
|-----|--------|------------|------------|
| Đào Văn Sơn | M1: Chunking + PDF ingestion | Có | Pass |
| Đào Văn Sơn | M2: Hybrid Search | Có | Pass |
| Đào Văn Sơn | M3: Reranking | Có | Pass |
| Đào Văn Sơn | M4: Evaluation | Có | Pass |
| Đào Văn Sơn | M5: Enrichment | Có | Pass |

Tổng kiểm thử: `42/42` tests passed.

## Kết quả RAGAS

| Metric | Naive | Production | Delta |
|--------|-------|------------|-------|
| Faithfulness | 1.0000 | 1.0000 | +0.0000 |
| Answer Relevancy | 0.7396 | 0.8229 | +0.0833 |
| Context Precision | 0.8750 | 0.7917 | -0.0833 |
| Context Recall | 1.0000 | 0.7007 | -0.2993 |

## Key Findings

1. **Biggest improvement:** Production pipeline cải thiện `answer_relevancy` từ `0.7396` lên `0.8229` nhờ có hybrid search, reranking và enrichment trước khi index.
2. **Biggest challenge:** Dữ liệu gốc là PDF scan tiếng Việt. `BCTC.pdf` gần như không có text layer, còn nghị định 39 trang cũng là ảnh scan, nên cần thêm ingestion layer để chuyển tài liệu thành Markdown có cấu trúc trước khi chunk.
3. **Surprise finding:** Với bảng BCTC, nếu chunk theo trang thì bảng bị đứt giữa trang 1 và trang 2. Cách tốt hơn là ghép bảng thành một Markdown table duy nhất, giữ các chỉ tiêu `[40]`, `[41]`, `[42]`, `[43]`.

## Pipeline Hiện Tại

Pipeline đã chạy end-to-end:

```text
PDF/official text ingestion -> M1 chunking -> M5 enrichment -> M2 hybrid search -> M3 rerank -> M4 evaluation
```

Dữ liệu sau xử lý:

| Loại dữ liệu | Số lượng |
|-------------|----------|
| Structured documents | 48 |
| Structure chunks | 48 |
| Hierarchical child chunks | 343 |

Nghị định 13/2023/NĐ-CP hiện được lưu đủ `Điều 1` đến `Điều 44` và `Phụ lục`. Bảng `BCTC.pdf` được lưu thành Markdown table, có metadata `continued_across_pages=true`.

## Presentation Notes

1. **RAGAS scores:** Faithfulness đạt `1.0000`; answer relevancy tăng `+0.0833` so với baseline.
2. **Biggest win:** M1 + ingestion là phần quan trọng nhất vì dữ liệu PDF scan ban đầu không thể chunk trực tiếp. Khi chuyển sang Markdown có cấu trúc, pipeline mới có dữ liệu để search.
3. **Case study:** Câu “Dữ liệu cá nhân là gì?” bị context recall thấp vì hierarchical chunk lấy các khoản sau của Điều 2 nhưng thiếu đúng khoản 1 định nghĩa trực tiếp.
4. **Next optimization:** Cải thiện chunking pháp lý theo khoản/điểm, đảm bảo mỗi câu hỏi định nghĩa luôn retrieve được khoản chứa định nghĩa chính.
