# Individual Reflection — Đào Văn Sơn - 2A202600032


---

## 1. Role cụ thể trong nhóm

**Product & UX Lead** — Phụ trách thiết kế trải nghiệm người dùng (UX), xây dựng luồng hội thoại (Conversation Flow) và tối ưu hóa các kịch bản tương tác khách hàng cho VinFast AI Agent.

---

## 2. Phần phụ trách cụ thể (output rõ ràng)

1.  **Thiết kế Luồng Hội thoại Tuần tự (Sequential Probing)**: Trực tiếp xây dựng kiến trúc hội thoại "Chậm mà Chắc". Đảm bảo Agent chỉ thu thập đủ thông tin (Ngân sách -> Số chỗ -> Mục đích) mới đưa ra gợi ý xe, giúp trải nghiệm tư vấn giống như đang nói chuyện với một tư vấn viên cao cấp tại Showroom.
2.  **Xây dựng User Stories & Edge Cases**: Định nghĩa 4 luồng nghiệp vụ chính: Tư vấn mua xe, Đặt lịch bảo dưỡng, Giải đáp FAQ và Xử lý SOS. Đặc biệt là thiết kế kịch bản cho các tình huống "AI không hiểu" hoặc "Yêu cầu ngoài tầm xử lý" để chuyển hướng chuyên gia kịp thời.
3.  **Tối ưu trải nghiệm Phản hồi (Feedback UX)**: Phụ trách logic hiển thị và thu thập ý kiến khách hàng qua nút Like/Dislike. Phối hợp với AI/Backend để đảm bảo các "Bài học" (Lessons) từ người dùng được AI ghi nhớ và điều chỉnh phong cách phục vụ ngay trong các lượt chat sau.
4.  **Thiết kế Giao diện & Hiển thị (UI/UX Integration)**: Giám sát việc thực hiện giao diện Glassmorphism và cách trình bày thông số kỹ thuật dưới dạng bảng biểu Markdown để khách hàng dễ dàng so sánh các dòng xe VF 3, 5, 6, 7, 8, 9 một cách trực quan nhất.

---

## 3. SPEC phần nào mạnh nhất, phần nào yếu nhất?

**Mạnh nhất: Phần 2 — User Stories (4 paths).**
Chúng em đã thiết kế được các luồng đi rất chi tiết cho cả trường hợp "Happy Path" (AI đúng) và "Failure Path" (AI sai). Việc có một quy trình cụ thể để AI tự sửa sai (Correction Path) chính là điểm nhấn mạnh nhất về mặt trải nghiệm người dùng trong SPEC này.

**Yếu nhất: Phần 5 — ROI & Bài toán kinh tế.**
Dù đã tính toán được số lượng nhân sự cắt giảm, nhưng việc định lượng "Sự hài lòng của khách hàng" (User Satisfaction) vào một con số tiền cụ thể vẫn còn mang tính ước lệ. Cần có các chỉ số CSAT/NPS thực tế để làm nổi bật hơn giá trị của sản phẩm.

---

## 4. Đóng góp cụ thể khác

- **Tối ưu hóa Call-to-Action (CTA)**: Đề xuất và cài đặt logic gợi ý "Đăng ký lái thử" đúng thời điểm (ngay sau khi gợi ý xe phù hợp), giúp tăng tỷ lệ chuyển đổi từ chat sang trải nghiệm thực tế.
- **Micro-copywriting**: Chỉnh sửa ngôn ngữ của Agent để luôn giữ âm điệu chuyên nghiệp, lịch sự (xưng Em, gọi Anh/Chị) và đậm chất tinh thần phục vụ của VinFast.
- **Bug Hunter**: Phát hiện các lỗi về hiển thị bảng biểu trên mobile và lỗi input bị tự động điền liệu (auto-fill), phối hợp cùng team kỹ thuật để khắc phục triệt để.

---

## 5. 1 điều học được trong hackathon mà trước đó chưa biết

Em học được rằng **"Prompt Engineering thực chất là UX Design"**. Khi chúng ta thay đổi một câu lệnh hướng dẫn cho AI, chính là chúng ta đang thiết kế lại cách người dùng sẽ trải nghiệm hội thoại. AI không chỉ cần "thông minh", nó cần phải "tinh tế" và biết lắng nghe đúng lúc.

---

## 6. Nếu làm lại, đổi gì?

Em sẽ đầu tư nhiều thời gian hơn vào việc **A/B Testing các luồng hội thoại**. Ví dụ: Thử so sánh xem khách hàng thích được gợi ý 1 xe duy nhất hay được so sánh 3 xe cùng lúc. Việc có dữ liệu thực tế về sở thích khách hàng sẽ giúp thiết kế UX của Agent sắc bén hơn nhiều.

---

## 7. AI giúp gì? AI sai/mislead ở đâu?

**AI giúp:**
- **Brainstorming User Stories**: Gợi ý các tình huống khách hàng khó tính hoặc các câu hỏi "oái oăm" để team chuẩn bị kịch bản ứng phó.
- **Generate Mock Content**: Tạo ra các đoạn hội thoại mẫu (Sample Dialogues) để kiểm tra độ trôi chảy của luồng tư vấn.
- **CSS Suggestions**: Hỗ trợ tìm các hex màu và hiệu ứng kính mờ (backdrop-filter) cho giao diện thêm phần sang trọng.

**AI sai/mislead:**
- AI ban đầu thường trả lời quá dài dòng và cung cấp quá nhiều thông tin cùng lúc, vi phạm triết lý "Tối giản" mà em hướng tới. Phải mất nhiều lượt tinh chỉnh prompt để ép AI chỉ được phép hỏi **MỘT** câu mỗi lần, đúng theo tinh thần tư vấn từng bước.
- **Bài học**: AI có xu hướng "tham công tiếc việc", vai trò của người thiết kế UX là phải đặt ra các ranh giới để giữ cho trải nghiệm người dùng luôn tập trung và dễ chịu.
