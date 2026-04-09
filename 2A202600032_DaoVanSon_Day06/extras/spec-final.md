# SPEC — AI Product Hackathon

**Nhóm:** ___
**Track:** ☑ VinFast
**Problem statement (1 câu):** Người mua xe điện VinFast mất nhiều thời gian tra cứu và so sánh thông số từ nhiều nguồn khác nhau — AI Advisor giúp họ tìm được mẫu xe phù hợp trong 1 cuộc hội thoại, thay thế 30–60 phút tự tìm kiếm.

---

## 1. AI Product Canvas

|   | Value | Trust | Feasibility |
|---|-------|-------|-------------|
| **Core** | **User:** Người có nhu cầu mua xe điện VinFast lần đầu (30–50 tuổi), chưa quen với xe EV. **Pain:** Phải tra cứu nhiều trang, so sánh thủ công, không biết mẫu nào phù hợp ngân sách + nhu cầu gia đình. **Value:** Chatbot hỏi nhu cầu → gợi ý 1–3 mẫu phù hợp + giải thích tại sao → dẫn thẳng đến hành động (lái thử / trả góp). | **Khi sai:** Gợi ý sai mẫu xe (VD: gợi ý VF3 cho gia đình 6 người). User thấy ngay vì chatbot hiển thị thông số rõ ràng (số chỗ, giá). User nói "không phù hợp" → chatbot hỏi lại nhu cầu. **Sửa:** User cung cấp thêm thông tin → chatbot re-recommend. | **Cost:** ~$0.001–$0.01/conversation (Gemini 1.5 Flash). **Latency:** <3s/turn. **Risk chính:** (1) Dữ liệu giá/thông số xe lỗi thời → tư vấn sai. (2) Hallucination thông số kỹ thuật. **Mitigation:** Source of truth = structured JSON; LLM không tự tạo thông số. |
| **Chốt** | **Augmentation** — chatbot gợi ý, user quyết định. Cost of reject = 0. User luôn có thể xem website VinFast để xác nhận. | **4-path:** xem User Stories bên dưới. | **Recall-first** trong recommendation (không bỏ sót xe phù hợp tệ hơn là gợi ý nhầm). |

**Automation hay Augmentation?** ☑ Augmentation

**Justify:** Quyết định mua xe là quyết định tài chính lớn (500M–2 tỷ VND). Chatbot chỉ làm vai trò tư vấn viên — user vẫn phải lái thử, đến showroom, ký hợp đồng. Nếu automation (chatbot tự đặt cọc) → rủi ro sai không thể hoàn tác. Cost of augmentation rejection = 0, user mất ≤1 phút đọc gợi ý sai.

**Learning signal:**

| # | Câu hỏi | Trả lời |
|---|---------|---------|
| 1 | Correction đi vào đâu? | User nói "không phù hợp" / "cho tôi xem thêm" / chọn xe khác → log conversation correction → cải thiện recommendation logic |
| 2 | Product thu signal gì? | Implicit: user có click CTA "lái thử" không? Có tiếp tục hỏi sau recommendation không? Explicit: thumbs up/down ở cuối recommendation. Alert khi CTR CTA < 20%. |
| 3 | Data loại nào? | Domain-specific (thông số xe VinFast) + User-specific (preferences từng user). Marginal value **cao** — LLM chung không biết giá VF8 hiện tại tại Việt Nam. |

---

## 2. User Stories — 4 paths

### Feature 1: Gợi ý xe phù hợp (Recommendation)

**Trigger:** User mô tả nhu cầu → chatbot hỏi đủ thông tin → gợi ý 1–3 mẫu xe

| Path | Câu hỏi thiết kế | Mô tả |
|------|------------------|-------|
| **Happy — AI đúng, tự tin** | User thấy gì? Flow kết thúc ra sao? | User nói: "Gia đình 5 người, ngân sách 1.2 tỷ, hay đi xa." → Chatbot gợi ý VF8 (95% match) + giải thích rõ: "Quãng đường 471km, 5 chỗ, giá 1.211 tỷ." → User hài lòng, click "Đăng ký lái thử" |
| **Low-confidence — AI không chắc** | System báo "không chắc" bằng cách nào? | User nói: "Tôi muốn xe tiết kiệm." → Chatbot nhận ra thiếu ngân sách và số chỗ → Hỏi lại: "Bạn dự kiến ngân sách bao nhiêu? Gia đình mấy người?" → Không gợi ý khi chưa đủ thông tin |
| **Failure — AI sai** | User biết AI sai bằng cách nào? Recover ra sao? | Chatbot hiểu sai "5 người" = 5 chỗ → gợi ý VF8 → User nói: "Nhưng tôi cần 7 chỗ vì có ông bà đi cùng." → Chatbot nhận correction → Gợi ý lại VF9. Hậu quả: 1–2 turns thêm, không mất thông tin. |
| **Correction — user sửa** | User sửa bằng cách nào? Data đó đi vào đâu? | User nói "không phù hợp" hoặc "cho tôi xe khác" → chatbot hỏi "Điều gì chưa phù hợp?" → User cho thêm context → preferences được update → re-recommend → log correction cho cải thiện sau |

### Feature 2: So sánh xe (Comparison)

**Trigger:** User đề cập 2 mẫu xe cụ thể hoặc hỏi "nên chọn A hay B"

| Path | Câu hỏi thiết kế | Mô tả |
|------|------------------|-------|
| **Happy — AI đúng, tự tin** | User thấy gì? | User: "So sánh VF8 và VF9 cho tôi." → Chatbot trả bảng so sánh rõ ràng: giá, chỗ, quãng đường, kích thước → Kết luận: "Chọn VF9 nếu gia đình ≥6 người, VF8 nếu 4–5 người và hay đi phố." → User hiểu ngay. |
| **Low-confidence** | Thiếu dữ liệu để so sánh? | User hỏi so sánh mẫu xe chưa có trong data (VD: VF Wild) → Chatbot: "Tôi chưa có đủ thông số chi tiết về mẫu này. Bạn xem tại [link] hoặc gọi 1900 23 23 89." |
| **Failure — AI sai** | AI dùng sai thông số? | Chatbot nhầm range VF8 (dùng số WLTP thay vì thực tế Việt Nam) → User biết vì đã xem website → Nói "Thông số sai rồi" → Chatbot xin lỗi + confirm lại từ nguồn và thêm disclaimer "Quãng đường thực tế phụ thuộc điều kiện lái." |
| **Correction** | User chỉnh sai sót? | User sửa → chatbot ghi nhận + xin lỗi + không bảo vệ thông tin sai → Đây là signal quan trọng để update data layer |

### Feature 3: Trả lời FAQ / Chính sách

**Trigger:** User hỏi về bảo hành, sạc điện, trả góp, lái thử...

| Path | Câu hỏi thiết kế | Mô tả |
|------|------------------|-------|
| **Happy** | | User: "Bảo hành VinFast bao lâu?" → Chatbot: "10 năm / 200.000 km, nguồn từ trang chính thức VinFast." → Rõ ràng, có nguồn. |
| **Low-confidence** | Chính sách có thể thay đổi? | User hỏi thuế trước bạ → Chatbot trả lời nhưng thêm: "⚠️ Chính sách thuế có thể thay đổi theo thời điểm. Vui lòng xác nhận tại thời điểm mua." |
| **Failure** | Chính sách đã thay đổi, data cũ? | Chatbot trả lời theo FAQ cũ → User nói "Tôi vừa gọi showroom, họ nói khác." → Chatbot: "Cảm ơn bạn đã phản hồi. Thông tin có thể đã thay đổi. Vui lòng xác nhận tại showroom hoặc website chính thức." |
| **Correction** | | User correction → log vào flagged_items → team update FAQ data manually |

---

## 3. Eval metrics + threshold

**Optimize precision hay recall?** ☑ Recall trong recommendation

**Tại sao?** Bỏ sót mẫu xe phù hợp tệ hơn gợi ý thêm 1 mẫu không hoàn hảo. Nếu chatbot precision quá cao → chỉ gợi ý 1 xe → user không có lựa chọn so sánh → mất trust. Nếu recall cao → gợi ý 2–3 xe đủ tiêu chí → user tự chọn → phù hợp với augmentation model.

**Nếu chọn precision nhưng low recall:** User không thấy xe phù hợp → nghĩ chatbot không biết → bỏ dùng. Đây là silent failure nguy hiểm hơn.

| Metric | Threshold | Red flag (dừng khi) |
|--------|-----------|---------------------|
| Recommendation relevance (user acceptance rate) | ≥70% user không reject lần đầu | <50% trong 3 ngày liên tiếp |
| CTA click-through rate (lái thử / trả góp) | ≥25% conversation có ≥1 CTA click | <10% → chatbot không dẫn được user đến action |
| Hallucination rate (thông số sai so với data) | 0% — zero tolerance | Bất kỳ instance nào tư vấn sai giá/thông số > 10% → ngừng ngay, review prompt |

**Lưu ý đặc biệt về hallucination:** Đây là metric zero-tolerance vì:
- Sai giá xe → user ra quyết định tài chính sai → mất trust không thể cứu vãn
- LLM được cấu hình để CHỈ dùng data từ products.json, không tự generate thông số

---

## 4. Top 3 failure modes

| # | Trigger | Hậu quả | Mitigation |
|---|---------|---------|------------|
| 1 | **[SILENT] Chatbot tự tin tư vấn mẫu xe đúng nhưng giá/thông số đã thay đổi** (VinFast cập nhật giá, chatbot vẫn dùng data cũ) | User ra quyết định dựa trên giá sai → đến showroom thấy giá khác → mất trust hoàn toàn. **User không biết đang bị sai.** | (1) Thêm timestamp vào mọi giá/thông số. (2) Hiển thị disclaimer: "Giá tham khảo, xác nhận tại thời điểm mua." (3) Alert khi data > 30 ngày chưa update. |
| 2 | **Chatbot hiểu sai nhu cầu mơ hồ** (VD: User nói "xe gia đình" — chatbot không hỏi rõ số người, gợi ý VF8 5 chỗ cho gia đình 7 người) | Recommendation sai từ đầu → user thất vọng → có thể rời chatbot trước khi sửa. | Mandatory clarification: KHÔNG gợi ý xe khi chưa có budget + seats. Nếu thiếu → hỏi lại, không đoán. Threshold: confidence < "medium" → phải hỏi tiếp. |
| 3 | **[SILENT] LLM hallucinate thông số ngoài dữ liệu** (VD: user hỏi thông số VF6, LLM tự tạo range_km không có trong data) | User nhận thông tin sai, tự tin cao, ra quyết định sai. **User không biết.** | (1) Strict guardrail: prompt yêu cầu LLM chỉ dùng data được cung cấp, không extrapolate. (2) Với mẫu xe có confidence = ASSUMPTION: luôn thêm "cần xác minh". (3) Nếu câu hỏi không có trong data → trả lời "Tôi không có thông tin này" thay vì đoán. |

---

## 5. ROI 3 kịch bản

|   | Conservative | Realistic | Optimistic |
|---|-------------|-----------|------------|
| **Assumption** | 50 users/ngày, 40% đến showroom sau chat, 10% mua xe | 200 users/ngày, 50% đến showroom, 15% mua xe | 500 users/ngày, 60% đến showroom, 20% mua xe |
| **Cost/ngày** | ~$5 (inference + hosting) = ~115K VND | ~$20 = ~460K VND | ~$50 = ~1.15M VND |
| **Benefit/ngày** | 50 × 40% × 10% × [thời gian tư vấn viên tiết kiệm ~30 phút = 75K VND] = ~75K VND tiết kiệm nhân sự. Plus: 50×10%×1 xe bán = ~50 xe/tháng tăng incremental nếu chatbot convert 5% extra. | 200 × 50% × 15% = 15 xe/ngày potential → nếu chatbot đóng góp 3% tăng thêm = ~3 xe/ngày × margin | 500 × 60% × 20% = 60 potential buyers/ngày |
| **Net (monthly)** | ~+1.8M tiết kiệm tư vấn viên - 3.45M chi phí = **-1.65M VND** (cần scale hơn) | ~+tăng conversion 3% × 200 xe/tháng × margin 5M/xe = **+30M VND net** | ~+tăng conversion 5% × 1000 xe/tháng × margin = **+100M+ VND** |

**Kill criteria:**
1. Hallucination rate > 0% (bất kỳ instance nào tư vấn sai thông số có xác minh) → ngừng ngay
2. CTA click-through < 10% sau 2 tuần → product không dẫn được user đến action → pivot hoặc dừng
3. User satisfaction < 3/5 sao sau 1 tháng → redesign conversation flow
4. Cost > benefit 3 tháng liên tiếp ở mức conservative → xem xét dừng

**Lưu ý về ROI hackathon:** Scenario conservative âm chủ yếu vì scale nhỏ và chưa tính conversion lift đủ. Với VinFast ở scale thật (hàng nghìn users/ngày), ROI rõ ràng dương khi chatbot thay thế 50% load tư vấn viên cơ bản.

---

## 6. Mini AI spec (1 trang)

**VinFast AI Car Advisor** là chatbot tư vấn mua xe điện VinFast theo mô hình **augmentation**: AI làm phần tốn thời gian (lọc xe, so sánh thông số, trả lời FAQ), con người quyết định (lái thử, chốt mua).

**Giải quyết vấn đề gì:** Người mua xe EV lần đầu mất 30–60 phút tra cứu thủ công qua nhiều trang. Chatbot rút ngắn xuống 3–5 phút hội thoại.

**Cho ai:** Người 30–50 tuổi đang cân nhắc mua xe EV VinFast, chưa quen với ecosystem EV (sạc ở đâu, pin bao lâu, bảo hành thế nào).

**AI làm gì (augmentation, không automation):**
- Hỏi nhu cầu có cấu trúc (budget, seats, use case)
- Lọc và xếp hạng xe phù hợp từ structured data
- Diễn đạt gợi ý tự nhiên bằng LLM
- Trả lời FAQ từ knowledge base có kiểm duyệt
- Dẫn user đến CTA đúng lúc (lái thử / trả góp)

**Chất lượng:** Recall-first trong recommendation (không bỏ sót xe phù hợp). Zero-tolerance hallucination (LLM chỉ dùng structured data). Khi không chắc → phải nói "cần xác minh".

**Rủi ro chính:**
1. Data staleness (giá/chính sách thay đổi) → disclaimer bắt buộc + alert 30 ngày
2. Hiểu sai nhu cầu mơ hồ → mandatory clarification trước khi recommend
3. LLM tự bịa thông số → strict prompt guardrail + source injection

**Data flywheel:**
User corrections → log → weekly review → update recommendation weights + FAQ data → chatbot tốt hơn → user acceptance tăng → loop.

**Prototype level:** Working prototype (Streamlit + Gemini 1.5 Flash + structured JSON data). Demo: live conversation, real AI call, CTA links đến website VinFast chính thức.
