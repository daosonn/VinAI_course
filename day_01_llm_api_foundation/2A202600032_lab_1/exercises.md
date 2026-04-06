# Ngày 1 — Bài Tập & Phản Ánh
## Nền Tảng LLM API | Phiếu Thực Hành

**Thời lượng:** 1:30 giờ  
**Cấu trúc:** Lập trình cốt lõi (60 phút) → Bài tập mở rộng (30 phút)

---

## Phần 1 — Lập Trình Cốt Lõi (0:00–1:00)

Chạy các ví dụ trong Google Colab tại: https://colab.research.google.com/drive/172zCiXpLr1FEXMRCAbmZoqTrKiSkUERm?usp=sharing

Triển khai tất cả TODO trong `template.py`. Chạy `pytest tests/` để kiểm tra tiến độ.

**Điểm kiểm tra:** Sau khi hoàn thành 4 nhiệm vụ, chạy:
```bash
python template.py
```
Bạn sẽ thấy output so sánh phản hồi của GPT-4o và GPT-4o-mini.

---

## Phần 2 — Bài Tập Mở Rộng (1:00–1:30)

### Bài tập 2.1 — Độ Nhạy Của Temperature
Gọi `call_openai` với các giá trị temperature 0.0, 0.5, 1.0 và 1.5 sử dụng prompt **"Hãy kể cho tôi một sự thật thú vị về Việt Nam."**

**Bạn nhận thấy quy luật gì qua bốn phản hồi?** (2–3 câu)
> Ở temperature 0.0, mô hình luôn trả về câu trả lời gần như giống hệt nhau, mang tính xác định cao và ít sáng tạo. Khi temperature tăng lên 0.5–1.0, phản hồi đa dạng hơn về từ ngữ và cách diễn đạt nhưng vẫn giữ nội dung chính xác. Ở temperature 1.5, câu trả lời trở nên phong phú, nhưng cũng có thể xuất hiện những diễn đạt kém tự nhiên hoặc kém chính xác hơn, thỉnh thoảng bị sai chính tả, dùng các ngôn ngữ của quốc gia khác.

**Bạn sẽ đặt temperature bao nhiêu cho chatbot hỗ trợ khách hàng, và tại sao?**
> Nên đặt temperature khoảng **0.2–0.3** vì chatbot hỗ trợ khách hàng cần ưu tiên tính nhất quán, chính xác và đáng tin cậy. Temperature thấp giúp mô hình bám sát thông tin sản phẩm/chính sách, tránh đưa ra câu trả lời mâu thuẫn hoặc sáng tạo quá mức có thể gây hiểu nhầm cho khách hàng.

---

### Bài tập 2.2 — Đánh Đổi Chi Phí
Xem xét kịch bản: 10.000 người dùng hoạt động mỗi ngày, mỗi người thực hiện 3 lần gọi API, mỗi lần trung bình ~350 token.

**Ước tính xem GPT-4o đắt hơn GPT-4o-mini bao nhiêu lần cho workload này:**
> Tổng token output mỗi ngày: 10.000 × 3 × 350 = **10.500.000 token**
> - Chi phí GPT-4o: (10.500.000 / 1.000) × $0.010 = **$105/ngày**
> - Chi phí GPT-4o-mini: (10.500.000 / 1.000) × $0.0006 = **$6.30/ngày**
>
> GPT-4o đắt hơn GPT-4o-mini khoảng **~16.7 lần** cho cùng workload này.

**Mô tả một trường hợp mà chi phí cao hơn của GPT-4o là xứng đáng, và một trường hợp GPT-4o-mini là lựa chọn tốt hơn:**
> **GPT-4o xứng đáng hơn:** Phân tích hợp đồng pháp lý hoặc báo cáo tài chính phức tạp — khi yêu cầu lập luận nhiều bước, hiểu ngữ cảnh dài và độ chính xác cao, sai sót có thể gây hậu quả nghiêm trọng.
>
> **GPT-4o-mini phù hợp hơn:** Phân loại email hỗ trợ khách hàng, tóm tắt nội dung ngắn, hoặc trả lời câu hỏi FAQ đơn giản — những tác vụ có cấu trúc rõ ràng, không đòi hỏi lập luận sâu, và cần xử lý lượng lớn request với chi phí tối thiểu.

---

### Bài tập 2.3 — Trải Nghiệm Người Dùng với Streaming
**Streaming quan trọng nhất trong trường hợp nào, và khi nào thì non-streaming lại phù hợp hơn?** (1 đoạn văn)
> Streaming quan trọng nhất trong các ứng dụng tương tác trực tiếp với người dùng như chatbot, trợ lý ảo, hay công cụ viết lách — nơi người dùng phải chờ đợi và cần cảm giác phản hồi tức thì để tránh cảm giác "lag". Khi phản hồi dài (500+ token), streaming giúp người dùng bắt đầu đọc ngay từ những từ đầu tiên thay vì chờ toàn bộ văn bản. Ngược lại, non-streaming phù hợp hơn khi xử lý batch (phân tích hàng loạt văn bản), khi kết quả cần hoàn chỉnh trước khi dùng (ví dụ: sinh code rồi chạy ngay, parse JSON từ output), hoặc trong các pipeline tự động không có người dùng trực tiếp quan sát — lúc đó overhead của streaming không mang lại giá trị gì.


## Danh Sách Kiểm Tra Nộp Bài
- [ ] Tất cả tests pass: `pytest tests/ -v`
- [ ] `call_openai` đã triển khai và kiểm thử
- [ ] `call_openai_mini` đã triển khai và kiểm thử
- [ ] `compare_models` đã triển khai và kiểm thử
- [ ] `streaming_chatbot` đã triển khai và kiểm thử
- [ ] `retry_with_backoff` đã triển khai và kiểm thử
- [ ] `batch_compare` đã triển khai và kiểm thử
- [ ] `format_comparison_table` đã triển khai và kiểm thử
- [ ] `exercises.md` đã điền đầy đủ
- [ ] Sao chép bài làm vào folder `solution` và đặt tên theo quy định 
