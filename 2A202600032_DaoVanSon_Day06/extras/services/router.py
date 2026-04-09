"""
Intent Router — Định tuyến câu hỏi người dùng đến đúng handler

Fix: Unicode NFC normalization + thêm keyword không dấu để match mọi cách gõ.
"""

import unicodedata
import re
from enum import Enum


class Intent(Enum):
    GREETING          = "greeting"
    RECOMMEND_VEHICLE = "recommend_vehicle"
    COMPARE_VEHICLES  = "compare_vehicles"
    ASK_VEHICLE_SPECS = "ask_vehicle_specs"
    ASK_FAQ           = "ask_faq"
    ASK_FINANCING     = "ask_financing"
    ASK_TEST_DRIVE    = "ask_test_drive"
    ASK_SHOWROOM      = "ask_showroom"
    RECALL_MEMORY     = "recall_memory"
    MORE_DETAIL       = "more_detail"
    UNCLEAR           = "unclear"
    OUT_OF_SCOPE      = "out_of_scope"
    ASK_BUY           = "ask_buy"
    CONTACT_HUMAN     = "contact_human"


# ──────────────────────────────────────────────────────────
# Normalize: về NFC + lowercase + bỏ dấu câu thừa
# ──────────────────────────────────────────────────────────
def normalize(text: str) -> str:
    """NFC normalize + lowercase — đảm bảo so sánh Unicode nhất quán."""
    return unicodedata.normalize("NFC", text.lower().strip())


def remove_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt — để match cả khi user gõ không dấu."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _is_word_boundary(text: str, start: int, end: int) -> bool:
    """Kiểm tra vị trí match có nằm ở ranh giới từ không."""
    if start > 0 and text[start - 1].isalpha():
        return False
    if end < len(text) and text[end].isalpha():
        return False
    return True


def text_matches_any(text: str, keywords: list[str]) -> bool:
    """
    Kiểm tra text có chứa keyword nào không.
    So sánh cả bản có dấu (NFC) lẫn bản không dấu.
    Từ ngắn (≤3 ký tự) dùng word-boundary matching để tránh false positive.
    """
    t_nfc  = normalize(text)
    t_bare = remove_accents(t_nfc)

    for kw in keywords:
        kw_nfc  = normalize(kw)
        kw_bare = remove_accents(kw_nfc)

        for t, k in [(t_nfc, kw_nfc), (t_bare, kw_bare)]:
            pos = t.find(k)
            if pos >= 0:
                if _is_word_boundary(t, pos, pos + len(k)):
                    return True
    return False


# ──────────────────────────────────────────────────────────
# Keyword lists  (có dấu + không dấu đều được nhận)
# ──────────────────────────────────────────────────────────
INTENT_KEYWORDS = {
    Intent.COMPARE_VEHICLES: [
        "so sánh", "so sanh", "khác nhau", "khac nhau",
        "nên chọn", "nen chon", "so với", "so voi",
        "giữa", "giua", "compare", "vs", "khác biệt", "khac biet", 
        "tốt hơn", "tot hon", "chọn cái nào", "difference", "which one", "chon cai nao"
    ],
    Intent.ASK_TEST_DRIVE: [
        "lái thử", "lai thu", "test drive", "thử xe", "thu xe",
        "đặt lịch lái", "dat lich lai", "đăng ký lái", "dang ky lai",
        "book test", "lái thử xe", "lai thu xe",
    ],
    Intent.ASK_SHOWROOM: [
        "showroom", "đại lý", "dai ly", "cửa hàng", "cua hang",
        "trạm sạc", "tram sac", "sạc ở đâu", "sac o dau",
        "địa chỉ", "dia chi", "gần nhất", "gan nhat", "tìm showroom", "tim showroom",
    ],
    Intent.ASK_BUY: [
        "mua luôn", "mua luon", "link mua", "mua ở đâu", "mua o dau", 
        "đặt cọc", "dat coc", "đặt xe", "dat xe", "chốt", "mua ngay", "đặt mua",
        "buy now", "purchase"
    ],
    Intent.CONTACT_HUMAN: [
        "nhân viên", "nhan vien", "người thật", "nguoi that", "tư vấn viên", "tu van vien",
        "tổng đài", "tong dai", "ai đang", "ai dang", "gọi ai", "nói chuyện với",
        "human", "agent", "support"
    ],
    Intent.ASK_FINANCING: [
        "trả góp", "tra gop", "vay", "lãi suất", "lai suat",
        "lăn bánh", "lan banh", "thuế", "thue", "phí", "phi",
        "tài chính", "tai chinh", "installment", "loan",
        "monthly", "hàng tháng", "hang thang",
        "chi phí mua", "chi phi mua", "tổng chi phí", "tong chi phi",
        "trả trước", "tra truoc", "đặt cọc", "dat coc", "budget", "price"
    ],
    Intent.ASK_VEHICLE_SPECS: [
        "thông số", "thong so", "specs", "quãng đường", "quang duong",
        "pin", "kwh", "km", "tốc độ", "toc do",
        "sạc bao lâu", "sac bao lau", "công suất", "cong suat",
        "bao nhiêu chỗ", "bao nhieu cho", "kích thước", "kich thuoc",
        "dài", "rộng", "cao", "nặng", "nang",
        "range", "battery", "charging", "acceleration",
        "nội thất", "noi that", "trang bị", "trang bi",
        "giá", "gia", "giá bao nhiêu", "bao nhiêu tiền", "bao nhieu tien",
        "how much", "cost", "size"
    ],
    Intent.ASK_FAQ: [
        "bảo hành", "bao hanh", "warranty",
        "hỗ trợ", "ho tro", "chính sách", "chinh sach",
        "dịch vụ", "dich vu", "sửa chữa", "sua chua",
        "bảo dưỡng", "bao duong", "câu hỏi", "cau hoi", "faq",
        "an toàn", "an toan", "tiết kiệm điện", "tiet kiem dien",
        "giảm giá", "giam gia", "khuyến mãi", "khuyen mai",
        "ưu đãi", "uu dai", "promotion",
        "thuê pin", "thue pin",
    ],
}

GREETING_KEYWORDS = [
    "xin chào", "xin chao", "chào bạn", "chao ban", "chào", "chao",
    "hello", "hi", "hey", "good morning", "good afternoon",
    "alo", "chào buổi sáng", "chào buổi chiều",
]

# Dấu hiệu câu hỏi hoàn toàn ngoài phạm vi xe hơi / VinFast
OUT_OF_SCOPE_SIGNALS = [
    "thời tiết", "thoi tiet", "bóng đá", "bong da", "chiến tranh", "chien tranh",
    "nấu ăn", "nau an", "phim", "movie", "nhạc", "music",
    "chính trị", "chinh tri", "bitcoin", "crypto", "chứng khoán", "chung khoan",
    "tình yêu", "tinh yeu", "sức khỏe", "suc khoe",
]

RECOMMEND_SIGNALS = [
    # Có dấu
    "tìm xe", "mua xe", "chọn xe", "cần xe", "muốn mua",
    "ngân sách", "tư vấn", "gợi ý", "phù hợp",
    "gia đình", "đi làm", "đường dài", "đi phố",
    "mấy chỗ", "số chỗ", "bao nhiêu tiền",
    "xe nào", "nên mua", "phiên bản nào",
    # Không dấu
    "tim xe", "mua xe", "chon xe", "can xe", "muon mua",
    "ngan sach", "tu van", "goi y", "phu hop",
    "gia dinh", "di lam", "duong dai", "di pho",
    "may cho", "so cho", "bao nhieu tien",
    "xe nao", "nen mua",
    # English
    "budget", "recommend", "suggest", "which car", "best car",
    "suitable", "family car", "daily", "commute",
    # Không giới hạn
    "không giới hạn", "khong gioi han", "vô tư", "vo tu", "tùy ý", "no limit", "unlimited"
]

# Dấu hiệu hỏi lại thông tin đã nhớ
MEMORY_RECALL_SIGNALS = [
    "ngân sách của tôi", "ngan sach cua toi",
    "bạn nhớ gì", "ban nho gi", "bạn có nhớ", "ban co nho",
    "nhớ tôi", "nho toi", "biết tôi", "biet toi",
    "thông tin của tôi", "thong tin cua toi",
    "tôi đã nói gì", "toi da noi gi",
    "tôi muốn gì", "toi muon gi",
]

# Dấu hiệu yêu cầu chi tiết hơn
MORE_DETAIL_SIGNALS = [
    "chi tiết hơn", "chi tiet hon", "cụ thể hơn", "cu the hon",
    "rõ hơn", "ro hon", "detail", "more detail",
    "kỹ hơn", "ky hon", "sâu hơn", "sau hon",
    "đầy đủ hơn", "day du hon",
]

# VinFast model aliases
VEHICLE_IDS = {
    "vf3":  ["vf3", "vf 3", "vf-3"],
    "vf5":  ["vf5", "vf 5", "vf-5", "vf5 plus", "vf5plus"],
    "vf6":  ["vf6", "vf 6", "vf-6"],
    "vf7":  ["vf7", "vf 7", "vf-7"],
    "vf8":  ["vf8", "vf 8", "vf-8"],
    "vf9":  ["vf9", "vf 9", "vf-9"],
    "vfwild": ["vf wild", "vfwild", "vf-wild"],
}


def detect_mentioned_vehicles(text: str) -> list[str]:
    t = normalize(text)
    mentioned = []
    for vid, aliases in VEHICLE_IDS.items():
        if any(a in t for a in aliases):
            mentioned.append(vid)
    return mentioned


def route_intent(user_message: str, conversation_history: list = None) -> dict:
    """
    Phân loại intent.
    Returns: {intent, mentioned_vehicles, confidence, needs_clarification}
    """
    mentioned = detect_mentioned_vehicles(user_message)

    has_compare = text_matches_any(user_message, INTENT_KEYWORDS[Intent.COMPARE_VEHICLES])
    has_specs   = text_matches_any(user_message, INTENT_KEYWORDS[Intent.ASK_VEHICLE_SPECS])
    has_td      = text_matches_any(user_message, INTENT_KEYWORDS[Intent.ASK_TEST_DRIVE])
    has_show    = text_matches_any(user_message, INTENT_KEYWORDS[Intent.ASK_SHOWROOM])
    has_buy     = text_matches_any(user_message, INTENT_KEYWORDS[Intent.ASK_BUY])
    has_human   = text_matches_any(user_message, INTENT_KEYWORDS[Intent.CONTACT_HUMAN])
    has_fin     = text_matches_any(user_message, INTENT_KEYWORDS[Intent.ASK_FINANCING])
    has_faq     = text_matches_any(user_message, INTENT_KEYWORDS[Intent.ASK_FAQ])
    has_rec     = text_matches_any(user_message, RECOMMEND_SIGNALS)
    has_greet   = text_matches_any(user_message, GREETING_KEYWORDS)
    has_oos     = text_matches_any(user_message, OUT_OF_SCOPE_SIGNALS)
    has_recall  = text_matches_any(user_message, MEMORY_RECALL_SIGNALS)
    has_detail  = text_matches_any(user_message, MORE_DETAIL_SIGNALS)

    # R-3: Yêu cầu gặp nhân viên
    if has_human:
        return _out(Intent.CONTACT_HUMAN, [], "high", False)

    # R-2: Yêu cầu mua xe (ưu tiên cao nhất)
    if has_buy:
        return _out(Intent.ASK_BUY, mentioned, "high", False)

    # R-1: Hỏi lại thông tin đã nhớ (ưu tiên cao)
    if has_recall:
        return _out(Intent.RECALL_MEMORY, [], "high", False)

    # R-0.5: Yêu cầu chi tiết hơn (follow-up)
    if has_detail and not mentioned:
        return _out(Intent.MORE_DETAIL, [], "medium", False)

    # R0: Chào hỏi đơn thuần (chỉ khi KHÔNG kèm intent khác)
    if has_greet and not any([has_compare, has_specs, has_td, has_show, has_fin, has_faq, has_rec]) and not mentioned:
        return _out(Intent.GREETING, [], "high", False)

    # R0.5: Hoàn toàn ngoài phạm vi (không liên quan xe) — check TRƯỚC greeting catch-all
    if has_oos and not has_rec and not mentioned and not has_fin and not has_faq:
        return _out(Intent.OUT_OF_SCOPE, [], "high", False)

    # R1: So sánh (cần ≥2 xe hoặc keyword so sánh rõ)
    if has_compare and len(mentioned) >= 2:
        return _out(Intent.COMPARE_VEHICLES, mentioned, "high", False)

    # R2: Hỏi thông số xe cụ thể
    if has_specs and len(mentioned) == 1:
        return _out(Intent.ASK_VEHICLE_SPECS, mentioned, "high", False)

    # R3: Lái thử (trước single-vehicle catch-all)
    if has_td:
        return _out(Intent.ASK_TEST_DRIVE, mentioned, "high", False)

    # R4: Showroom / trạm sạc
    if has_show:
        return _out(Intent.ASK_SHOWROOM, [], "high", False)

    # R5: Tài chính / trả góp — ĐẶT TRƯỚC single-vehicle catch-all
    #     Để "tra gop vf8" route đúng tới FINANCING thay vì SPECS
    if has_fin:
        return _out(Intent.ASK_FINANCING, mentioned, "high", False)

    # R6: FAQ / chính sách (trước single-vehicle catch-all)
    if has_faq:
        return _out(Intent.ASK_FAQ, mentioned, "medium", False)

    # R7: Nhắc đúng 1 xe (kể cả "tư vấn VF3") → hỏi info/specs về xe đó
    if len(mentioned) == 1 and not has_compare:
        return _out(Intent.ASK_VEHICLE_SPECS, mentioned, "high" if has_specs else "medium", False)

    # R8: Recommend — có tín hiệu nhu cầu nhưng không nhắc xe cụ thể
    if has_rec:
        return _out(Intent.RECOMMEND_VEHICLE, mentioned, "medium", True)

    # R9: Hỏi specs nhưng không nhắc xe nào -> dựa vào context (memory)
    if has_specs:
        return _out(Intent.ASK_VEHICLE_SPECS, mentioned, "low", False)

    # R10: So sánh nhưng thiếu tên xe
    if has_compare:
        return _out(Intent.COMPARE_VEHICLES, mentioned, "low", True)

    # R10: Có tên xe nhưng không rõ intent
    if len(mentioned) >= 2:
        return _out(Intent.COMPARE_VEHICLES, mentioned, "medium", False)

    # Fallback
    return _out(Intent.UNCLEAR, [], "low", True)


def _out(intent, vehicles, confidence, needs_clarification):
    return {
        "intent": intent,
        "mentioned_vehicles": vehicles,
        "confidence": confidence,
        "needs_clarification": needs_clarification,
    }


def get_clarification_question(intent_result: dict, existing_preferences: dict = None) -> str:
    intent = intent_result["intent"]

    if intent == Intent.GREETING:
        return (
            "Xin chào! 👋 Tôi là **VinFast AI Advisor** — trợ lý tư vấn mua xe điện.\n\n"
            "Tôi có thể giúp bạn:\n"
            "- 🚗 **Tư vấn** chọn xe phù hợp theo nhu cầu\n"
            "- 📊 **So sánh** các mẫu VF3 đến VF9\n"
            "- 💡 **Giải đáp** giá, thông số, sạc điện, bảo hành\n"
            "- 📅 **Đăng ký** lái thử & tìm showroom\n\n"
            "Bạn đang quan tâm đến dòng xe nào, hoặc cần tôi tư vấn từ đầu?"
        )

    if intent == Intent.OUT_OF_SCOPE:
        return (
            "Xin lỗi, tôi chỉ có thể hỗ trợ về **xe điện VinFast** thôi ạ. 😊\n\n"
            "Bạn có muốn tôi tư vấn chọn xe, so sánh mẫu xe, hay giải đáp thắc mắc về VinFast không?"
        )

    if intent == Intent.RECOMMEND_VEHICLE:
        if not existing_preferences:
            return (
                "Để tư vấn chính xác, bạn cho tôi biết:\n"
                "- **Ngân sách** dự kiến là bao nhiêu?\n"
                "- Gia đình bạn có **mấy người** thường đi cùng?"
            )
        prefs = existing_preferences
        if not prefs.get("budget_vnd") and not prefs.get("unlimited_budget"):
            return "Bạn dự kiến **ngân sách** khoảng bao nhiêu cho chiếc xe này?"
        if not prefs.get("seats_needed"):
            return "Gia đình bạn thường đi **mấy người**? Tôi sẽ gợi ý đúng số chỗ hơn."
        if not prefs.get("use_cases"):
            return (
                "Bạn chủ yếu dùng xe để làm gì?\n"
                "- 🏙️ Đi làm nội thành hàng ngày\n"
                "- 👨‍👩‍👧 Đưa đón gia đình\n"
                "- 🛣️ Thường xuyên đi đường dài liên tỉnh"
            )
        return "Còn điều gì bạn đặc biệt quan tâm không? (quãng đường, nội thất, giá...)"

    elif intent == Intent.COMPARE_VEHICLES:
        if len(intent_result.get("mentioned_vehicles", [])) < 2:
            return "Bạn muốn so sánh mẫu xe nào? Ví dụ: **VF8 và VF9**, hoặc **VF6 và VF7**?"

    elif intent == Intent.UNCLEAR:
        return (
            "Bạn cần tôi hỗ trợ gì về xe VinFast?\n\n"
            "- 🚗 Tư vấn chọn xe phù hợp\n"
            "- 📊 So sánh 2–3 mẫu xe\n"
            "- 💡 Thông tin giá, thông số kỹ thuật\n"
            "- 📅 Đăng ký lái thử\n"
            "- 📍 Tìm showroom / trạm sạc\n"
            "- 💰 Tính trả góp / chi phí lăn bánh"
        )

    return None
