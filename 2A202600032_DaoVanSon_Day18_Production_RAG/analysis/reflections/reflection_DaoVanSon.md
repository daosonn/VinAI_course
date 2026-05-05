# Individual Reflection - Lab 18

**Tên:** Đào Văn Sơn  
**Module phụ trách:** M1, M2, M3, M4, M5 và pipeline tích hợp  
**Hình thức:** Làm cá nhân

## 1. Đóng góp kỹ thuật

- Implement M1 chunking: `chunk_semantic()`, `chunk_hierarchical()`, `chunk_structure_aware()`, `compare_strategies()`.
- Thêm ingestion layer cho dữ liệu PDF scan tiếng Việt trong `src/pdf_ingestion.py`.
- Chuyển `BCTC.pdf` thành Markdown table, giữ bảng vắt qua trang 1-2 và bảo toàn các mã `[40]`, `[41]`, `[42]`, `[43]`.
- Bổ sung full text Nghị định 13/2023/NĐ-CP từ bản Công báo chính thức, tách đủ `Điều 1` đến `Điều 44` và `Phụ lục`.
- Implement M2 hybrid search gồm BM25 tiếng Việt, dense fallback và reciprocal rank fusion.
- Implement M3 reranking fallback, M4 evaluation fallback, M5 enrichment fallback.
- Viết script `scripts/export_processed_data.py` để xuất OCR/structured docs và chunks ra Markdown cho việc kiểm tra thủ công.
- Số tests pass: `42/42`.

## 2. Kiến thức học được

- Khái niệm mới quan trọng nhất là RAG production pipeline không chỉ gồm embedding và LLM, mà còn cần ingestion, chunking, search, rerank, enrichment, evaluation và failure analysis.
- Với dữ liệu tiếng Việt scan PDF, bước OCR/ingestion quyết định chất lượng retrieval. Nếu PDF không có text layer, chunking trực tiếp sẽ thất bại.
- Với văn bản pháp lý, chunk theo cấu trúc `Điều/Khoản/Điểm` hợp lý hơn chunk cố định theo số ký tự.
- Với bảng tài chính hoặc tờ khai thuế, cần giữ nguyên bảng thành một block Markdown; nếu cắt theo trang hoặc theo ký tự, các dòng chỉ tiêu dễ mất ngữ cảnh.
- RAGAS/failure analysis giúp nhìn ra lỗi nằm ở retrieval, context, generation hay prompt, thay vì chỉ nhìn điểm tổng.

## 3. Khó khăn & Cách giải quyết

- **Khó khăn lớn nhất:** Hai PDF trong `data/` gần như là ảnh scan, nên text extraction bằng PyMuPDF trả về rất ít nội dung.
- **Cách giải quyết:** Tạo ingestion layer riêng. Với `BCTC.pdf`, dùng rule/template để phục hồi bảng GTGT thành Markdown. Với Nghị định 13, dùng bản `.doc` chính thức từ Cổng Công báo để có full text chuẩn, sau đó tách theo điều.
- **Khó khăn khi debug:** PaddleOCR trong môi trường hiện tại lỗi dependency, EasyOCR chưa có model local và tải model bị timeout.
- **Giải pháp tạm thời:** Giữ thiết kế hỗ trợ OCR, nhưng dùng nguồn official text để đảm bảo dữ liệu đầy đủ và pipeline chạy được ổn định.

## 4. Nếu làm lại

- Tôi sẽ bắt đầu bằng bước kiểm tra chất lượng dữ liệu: PDF có text layer hay scan ảnh, có bảng không, có nguồn official text khác không.
- Tôi sẽ tách ingestion thành bước bắt buộc trước M1, thay vì để M1 tự đọc PDF trực tiếp.
- Tôi muốn thử tiếp module query rewriting và legal-aware reranking, đặc biệt cho câu hỏi dạng định nghĩa như “Dữ liệu cá nhân là gì?”.
- Tôi cũng muốn thêm answer extraction riêng cho Markdown table để trả lời số liệu ngắn gọn hơn.

## 5. Tự đánh giá

| Tiêu chí | Tự chấm (1-5) |
|----------|---------------|
| Hiểu bài giảng | 5 |
| Code quality | 4 |
| Teamwork | 5 |
| Problem solving | 5 |

