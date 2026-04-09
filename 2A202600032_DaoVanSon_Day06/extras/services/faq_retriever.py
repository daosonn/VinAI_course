"""
FAQ Retriever — Retrieval nhẹ cho FAQ/Policy knowledge

Không dùng vector database cho MVP.
Dùng keyword matching + category routing — đủ tốt cho hackathon demo.
"""

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "faq.json"


@lru_cache(maxsize=1)
def load_faqs():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _remove_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt để match cả khi user gõ không dấu."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# Mapping từ khóa → category (để route nhanh)
CATEGORY_KEYWORDS = {
    "tai_chinh": [
        "trả góp", "vay", "lãi suất", "lăn bánh", "thuế trước bạ",
        "phí đăng ký", "tài chính", "installment", "chi phí mua"
    ],
    "sac_dien": [
        "sạc", "trạm sạc", "sạc ở đâu", "sạc tại nhà", "v-green",
        "evcs", "sạc nhanh", "dc", "ac", "wallbox", "tiền điện"
    ],
    "bao_hanh": [
        "bảo hành", "warranty", "bảo dưỡng", "sửa chữa", "lỗi",
        "hỏng", "dịch vụ sau bán"
    ],
    "lai_thu": [
        "lái thử", "test drive", "thử xe", "đăng ký lái", "đặt lịch lái"
    ],
    "showroom": [
        "showroom", "đại lý", "mua ở đâu", "địa chỉ", "cửa hàng"
    ],
    "mua_xe": [
        "mua xe", "đặt cọc", "đặt xe", "quy trình", "thủ tục",
        "hồ sơ", "giấy tờ", "thuê pin", "thue pin"
    ],
    "chi_phi_lan_banh": [
        "lăn bánh", "thuế", "phí đường bộ", "bảo hiểm", "tổng chi phí"
    ]
}


def detect_faq_category(query: str) -> list[str]:
    """Xác định category FAQ phù hợp từ câu hỏi.
    So sánh cả bản có dấu lẫn không dấu để match mọi cách gõ tiếng Việt."""
    query_bare = _remove_accents(query)
    matched_categories = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in query.lower() or _remove_accents(kw) in query_bare:
                matched_categories.append(category)
                break
    return matched_categories


def simple_text_match(query: str, faq: dict) -> int:
    """Tính điểm match đơn giản giữa query và FAQ item.
    So sánh cả có dấu và không dấu."""
    query_bare = _remove_accents(query)
    query_words = set(query_bare.split())
    question_words = set(_remove_accents(faq["question"]).split())
    answer_words = set(_remove_accents(faq["answer"][:200]).split())

    # Overlap với question được ưu tiên hơn
    q_overlap = len(query_words & question_words)
    a_overlap = len(query_words & answer_words)

    return q_overlap * 2 + a_overlap


def retrieve_faqs(query: str, top_n: int = 2) -> list[dict]:
    """
    Tìm FAQ phù hợp nhất với câu hỏi.

    Returns:
        List[faq_item] đã sắp xếp theo relevance
    """
    data = load_faqs()
    faqs = data["faqs"]

    # Step 1: Filter theo category
    matched_categories = detect_faq_category(query)
    if matched_categories:
        candidate_faqs = [f for f in faqs if f.get("category") in matched_categories]
    else:
        candidate_faqs = faqs  # Fallback: tìm trên toàn bộ

    if not candidate_faqs:
        candidate_faqs = faqs

    # Step 2: Score theo text match
    scored = []
    for faq in candidate_faqs:
        score = simple_text_match(query, faq)
        scored.append((score, faq))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Step 3: Chỉ trả về nếu score đủ cao (tránh irrelevant result)
    results = []
    for score, faq in scored[:top_n]:
        if score >= 1:  # Ít nhất 1 từ khớp
            results.append(faq)

    return results


def format_faq_for_prompt(faqs: list[dict]) -> str:
    """Format FAQ results để inject vào prompt LLM."""
    if not faqs:
        return "Không tìm thấy FAQ liên quan."

    lines = []
    for faq in faqs:
        lines.append(f"**Q: {faq['question']}**")
        lines.append(f"A: {faq['answer']}")
        if faq.get("disclaimer"):
            lines.append(f"⚠️ Lưu ý: {faq['disclaimer']}")
        if faq.get("source_url"):
            lines.append(f"Nguồn: {faq['source_url']}")
        lines.append("")

    return "\n".join(lines)


def get_cta_for_faq(faq: dict) -> dict | None:
    """Lấy CTA phù hợp cho FAQ item."""
    cta_map = {
        "installment_calculator": {
            "label": "Tính trả góp",
            "url": "https://shop.vinfastauto.com/vn_vi/installment-cost"
        },
        "test_drive_registration": {
            "label": "Đăng ký lái thử",
            "url": "https://shop.vinfastauto.com/vn_vi/dang-ky-lai-thu.html"
        },
        "charging_station_map": {
            "label": "Tìm trạm sạc",
            "url": "https://vinfastauto.com/vn_vi/he-thong-tram-sac"
        },
        "showroom_locator": {
            "label": "Tìm showroom",
            "url": "https://vinfastauto.com/vn_vi"
        },
        "rolling_cost_calculator": {
            "label": "Dự toán chi phí lăn bánh",
            "url": "https://shop.vinfastauto.com/vn_vi/installment-cost"
        },
        "compare_vehicles": {
            "label": "So sánh xe",
            "url": "https://vinfastauto.com/vn_vi/so-sanh-xe"
        }
    }

    cta_key = faq.get("cta")
    return cta_map.get(cta_key)
