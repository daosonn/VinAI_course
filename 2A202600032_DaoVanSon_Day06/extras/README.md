# VinFast AI Car Advisor — Hackathon Day 6

> Chatbot tư vấn mua xe điện VinFast theo kiến trúc 3 lớp: structured product data + FAQ knowledge + LLM orchestration

## Cấu trúc Project

```
Day06_product/
├── app.py                          # Streamlit app chính — entry point
├── spec-final.md                   # SPEC hoàn chỉnh 6 sections cho hackathon
├── prototype-readme.md             # Mô tả prototype, tools, phân công
├── demo-slides.md                  # Script demo 2-3 phút + Q&A
├── README.md                       # File này
│
├── data/
│   ├── products.json               # Source of truth: thông số 6 mẫu xe VinFast
│   ├── faq.json                    # Knowledge base: FAQ về mua xe, sạc, bảo hành
│   └── cta_links.json              # CTA links chính thức VinFast
│
├── prompts/
│   ├── system_prompt.txt           # System prompt cho chatbot
│   ├── extract_preferences.txt     # Prompt trích xuất nhu cầu user → JSON
│   ├── recommendation.txt          # Prompt sinh explanation gợi ý xe
│   └── comparison.txt              # Prompt so sánh 2-3 xe
│
└── services/
    ├── router.py                   # Intent detection (rule-based, không cần LLM)
    ├── recommender.py              # Recommendation engine (rule-based scoring)
    ├── faq_retriever.py            # FAQ retrieval (keyword matching)
    └── llm_client.py               # LLM wrapper (Gemini 1.5 Flash)
```

## Kiến trúc 3 lớp

```
Layer 1: Structured Product Data
  → data/products.json — 6 mẫu xe VinFast với thông số đầy đủ
  → Source of truth — LLM không được tự tạo thông số

Layer 2: FAQ / Policy Knowledge
  → data/faq.json — 12 FAQ về mua xe, sạc, bảo hành, trả góp
  → data/cta_links.json — Links chính thức đến website VinFast

Layer 3: LLM Orchestration (Gemini 1.5 Flash)
  → Hiểu nhu cầu → detect intent → chọn data layer phù hợp
  → Inject structured data vào prompt → LLM chỉ diễn đạt, không tự bịa
  → Sinh explanation + CTA phù hợp
```

## Cài đặt

```bash
pip install streamlit google-generativeai

# Set API key
export GEMINI_API_KEY=your_gemini_api_key

# Chạy
streamlit run app.py
```

Lấy Gemini API key miễn phí tại: https://aistudio.google.com/apikey

## Use cases demo

1. **Tư vấn chọn xe:**
   - "Gia đình 5 người, ngân sách 1.2 tỷ, hay đi xa" → Gợi ý VF8 + lý do
   - "Tôi đi làm nội thành, ngân sách 600 triệu" → Gợi ý VF3/VF5

2. **So sánh xe:**
   - "So sánh VF8 và VF9" → Bảng so sánh + kết luận rõ ràng

3. **FAQ:**
   - "Sạc xe ở đâu?" → Thông tin trạm sạc + link bản đồ
   - "Bảo hành bao lâu?" → 10 năm / 200.000 km

4. **CTA:**
   - Sau mỗi gợi ý: link đăng ký lái thử, tính trả góp

## Nguồn dữ liệu

- Giá xe VF3, VF7, VF8, VF9: **HIGH confidence** — xác minh từ nhiều nguồn
- Giá xe VF5, VF6: **MEDIUM/ASSUMPTION** — cần xác minh lại trên website chính thức
- FAQ: Tổng hợp từ vinfastauto.com/vn_vi + nguồn chính thức
- Links: Domain chính thức vinfastauto.com

⚠️ **Lưu ý:** Giá và chính sách VinFast có thể thay đổi. Chatbot luôn hiển thị disclaimer và hướng dẫn xác nhận tại website hoặc hotline 1900 23 23 89.
