# Failure Analysis - Lab 18: Production RAG

**Người thực hiện:** Đào Văn Sơn  
**Hình thức:** Làm cá nhân  
**Ngày:** 05/05/2026

## RAGAS Scores

| Metric | Naive Baseline | Production | Delta |
|--------|----------------|------------|-------|
| Faithfulness | 1.0000 | 1.0000 | +0.0000 |
| Answer Relevancy | 0.7396 | 0.8229 | +0.0833 |
| Context Precision | 0.8750 | 0.7917 | -0.0833 |
| Context Recall | 1.0000 | 0.7007 | -0.2993 |

## Bottom Failures

### #1 - Dữ liệu cá nhân là gì?

- **Question:** Dữ liệu cá nhân là gì?
- **Expected:** Dữ liệu cá nhân là thông tin gắn liền với một con người cụ thể hoặc giúp xác định một con người cụ thể.
- **Got:** Pipeline trả về context thuộc Điều 2 nhưng bắt đầu từ các khoản sau như “Bên thứ ba”, “Xử lý dữ liệu cá nhân tự động”, “Bên Kiểm soát dữ liệu cá nhân”, thay vì khoản 1 định nghĩa trực tiếp “Dữ liệu cá nhân là...”.
- **Worst metric:** `context_recall = 0.5263`
- **Error Tree:** Output chưa đúng trọng tâm -> Context có liên quan nhưng thiếu đúng khoản định nghĩa -> Query không sai -> Fix ở retrieval/chunking.
- **Root cause:** Hierarchical child chunk đang cắt Điều 2 theo kích thước, nên nội dung định nghĩa ở khoản 1 có thể nằm ở child khác, trong khi BM25/rerank chọn các child có nhiều cụm “dữ liệu cá nhân” hơn nhưng không chứa câu định nghĩa chính.
- **Suggested fix:** Chunk văn bản pháp lý theo đơn vị `Điều -> Khoản -> Điểm`, hoặc prepend `Điều 2. Giải thích từ ngữ` và số khoản vào từng child chunk. Với câu hỏi dạng “là gì”, ưu tiên chunk có pattern định nghĩa `X là ...`.

### #2 - Thuế GTGT còn được khấu trừ chuyển kỳ sau là bao nhiêu?

- **Question:** Thuế GTGT còn được khấu trừ chuyển kỳ sau là bao nhiêu?
- **Expected:** Thuế GTGT còn được khấu trừ chuyển kỳ sau tại chỉ tiêu `[43]` là `0` đồng.
- **Got:** Pipeline retrieve đúng bảng BCTC có dòng `[43]`, nhưng answer hiện là extractive context dài thay vì câu trả lời ngắn.
- **Worst metric:** `context_precision = 0.7500`
- **Error Tree:** Output có thông tin đúng nhưng dài -> Context đúng -> Query OK -> Fix ở generation/answer extraction.
- **Root cause:** `run_query()` đang dùng câu trả lời extractive bằng context đầu tiên, chưa có bước LLM hoặc rule đọc dòng bảng để rút ra giá trị cuối cùng.
- **Suggested fix:** Với bảng Markdown, thêm parser tìm dòng chứa `[43]` rồi sinh câu trả lời ngắn: “Chỉ tiêu [43] bằng 0 đồng.” Nếu dùng LLM, prompt cần yêu cầu trả lời ngắn và trích mã chỉ tiêu.

## Case Study Cho Presentation

**Question chọn phân tích:** Dữ liệu cá nhân là gì?

**Error Tree walkthrough:**

1. **Output đúng không?** Chưa đúng trọng tâm. Câu trả lời nói về các khái niệm liên quan trong Điều 2 nhưng chưa lấy đúng câu định nghĩa chính.
2. **Context đúng không?** Đúng tài liệu và đúng Điều 2, nhưng thiếu khoản 1 là đoạn quan trọng nhất.
3. **Query rewrite OK không?** Query rõ ràng, không cần rewrite phức tạp.
4. **Fix ở bước nào?** Fix ở chunking và reranking: chunk pháp lý theo khoản, thêm metadata `article`, `clause`, và ưu tiên pattern định nghĩa.

**Nếu có thêm 1 giờ sẽ optimize:**

- Tách legal chunks theo khoản/điểm thay vì chỉ theo size.
- Thêm rule rerank cho câu hỏi định nghĩa: ưu tiên câu chứa “là”.
- Thêm answer generator cho bảng: tìm dòng theo mã chỉ tiêu rồi trả lời ngắn.
- Mở rộng test set lên nhiều câu hỏi hơn để điểm RAGAS ổn định hơn.
