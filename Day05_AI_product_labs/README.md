# Day 05 — Submission

**Sản phẩm phân tích:** Vietnam Airlines — Chatbot NEO


---

## Cấu trúc repo

```
Day05/
├── README.md
├── ux-exercise/
│   └── analysis.md                    ← Phân tích 4 paths + gap marketing vs thực tế 
├── extras/
│   └── data-flywheel.md               ← Thiết kế Data Flywheel S1–S8 
└── document/
    ├── 4path.jpg                       ← Sketch phân tích 4 paths 
    ├── gap_sketch.jpg                  ← Sketch gap marketing vs thực tế 
    ├── improvement-sketch.jpg          ← Sketch as-is → to-be 
    ├── chatbot-improved.jpg            ← Screenshot chatbot sau cải tiến 
    └── data_flywheel.png               ← Sơ đồ Data Flywheel 
```

---

## Tóm tắt bài làm

### UX Exercise (10 điểm)
- **Sản phẩm:** Vietnam Airlines Chatbot NEO
- **Path yếu nhất:** Path 3 (AI sai) — không có feedback loop, không có correction mechanism
- **Gap:** Marketing hứa "trợ lý thông minh", thực tế là FAQ bot không có real-time data và không học từ lỗi
- **To-be:** Data Flywheel với 7 lớp system: Log → Feedback → Ground-truth → Session → Memory → Label → Pipeline

### Extras (bonus)
- Thiết kế chi tiết Data Flywheel (7 lớp S1–S8)
- Prototype chatbot đã implement đầy đủ logic trong `d:/Tailieutruong20252/Vin_AI/chatbot_ui/`

---

## Hình ảnh đã có trong `document/`

| File | Nội dung | Dùng trong |
|------|----------|------------|
| `4path.jpg` | Sketch phân tích 4 paths | analysis.md |
| `gap_sketch.jpg` | Sketch gap marketing vs thực tế | analysis.md |
| `improvement-sketch.jpg` | Sketch as-is → to-be (path 3 cải tiến) | analysis.md |
| `chatbot-improved.jpg` | Screenshot chatbot prototype sau cải tiến | analysis.md, data-flywheel.md |
| `data_flywheel.png` | Sơ đồ Data Flywheel S1–S8 | data-flywheel.md |

---

*Day 5 — VinUni A20 — AI Thực Chiến 2026*
