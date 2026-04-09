"""
Conversation Memory — Lưu trữ ngữ cảnh hội thoại cho chatbot

Memory gồm 2 tầng:
1. Structured preferences (budget, seats, use_case...) — cập nhật qua extract_preferences
2. Conversation summary — tóm tắt ngắn context hiện tại để inject vào LLM

Tại sao cần memory:
- Không hỏi lại những gì user đã nói ở turns trước
- LLM nhận đủ context ngay cả khi history bị cắt ngắn
- Hiển thị cho user thấy chatbot "đang nhớ gì"
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserMemory:
    # Preferences
    budget_vnd: Optional[int] = None
    budget_note: Optional[str] = None
    unlimited_budget: bool = False
    seats_needed: Optional[int] = None
    use_cases: list = field(default_factory=list)
    priorities: list = field(default_factory=list)
    daily_km: Optional[int] = None
    has_home_charging: Optional[bool] = None
    family_size: Optional[int] = None

    # Interaction history
    mentioned_vehicles: list = field(default_factory=list)   # xe đã hỏi/xem
    rejected_vehicles: list = field(default_factory=list)    # xe user nói không phù hợp
    last_recommended: list = field(default_factory=list)     # xe đã recommend gần nhất
    user_summary: str = ""                                   # Tổng hợp ngữ cảnh sở thích bằng LLM

    # Meta
    turn_count: int = 0
    confidence: str = "low"   # low | medium | high


def update_memory(memory: UserMemory, new_prefs: dict) -> UserMemory:
    """Merge preferences mới vào memory hiện tại."""
    if not new_prefs:
        return memory

    # Chỉ update nếu giá trị mới không None
    if "unlimited_budget" in new_prefs and new_prefs["unlimited_budget"]:
        memory.unlimited_budget = True
        memory.budget_vnd = 999_000_000_000
        memory.budget_note = "không giới hạn"
    elif new_prefs.get("budget_vnd"):
        memory.budget_vnd = new_prefs["budget_vnd"]
    if new_prefs.get("budget_note") and not memory.unlimited_budget:
        memory.budget_note = new_prefs["budget_note"]
    if new_prefs.get("seats_needed"):
        memory.seats_needed = new_prefs["seats_needed"]
    if new_prefs.get("use_cases"):
        # Merge (union) thay vì replace — không mất use case từ lượt trước
        for uc in new_prefs["use_cases"]:
            if uc not in memory.use_cases:
                memory.use_cases.append(uc)
    if new_prefs.get("priorities"):
        # Merge (union) thay vì replace — giữ ưu tiên đã nói ở lượt trước
        for pr in new_prefs["priorities"]:
            if pr not in memory.priorities:
                memory.priorities.append(pr)
    if new_prefs.get("daily_km"):
        memory.daily_km = new_prefs["daily_km"]
    if new_prefs.get("has_home_charging") is not None:
        memory.has_home_charging = new_prefs["has_home_charging"]
    if new_prefs.get("family_size"):
        memory.family_size = new_prefs["family_size"]
    if new_prefs.get("specific_model_interest"):
        for m in new_prefs["specific_model_interest"]:
            if m not in memory.mentioned_vehicles:
                memory.mentioned_vehicles.append(m)
    if new_prefs.get("confidence"):
        memory.confidence = new_prefs["confidence"]

    return memory


def format_memory_for_prompt(memory: UserMemory) -> str:
    """Tạo context string từ memory để inject vào LLM prompt."""
    lines = ["## THÔNG TIN ĐÃ BIẾT VỀ NGƯỜI DÙNG (từ hội thoại trước)"]

    if memory.budget_vnd:
        budget_m = memory.budget_vnd / 1_000_000
        lines.append(f"- Ngân sách: {budget_m:.0f} triệu VND"
                     + (f" ({memory.budget_note})" if memory.budget_note else ""))
    if memory.seats_needed:
        lines.append(f"- Số chỗ cần: {memory.seats_needed} chỗ")
    if memory.family_size:
        lines.append(f"- Gia đình: {memory.family_size} người")
    if memory.use_cases:
        uc_map = {
            "daily_city": "đi làm nội thành",
            "family": "gia đình",
            "long_distance": "đường dài liên tỉnh",
            "business": "kinh doanh"
        }
        uc_str = ", ".join([uc_map.get(uc, uc) for uc in memory.use_cases])
        lines.append(f"- Mục đích sử dụng: {uc_str}")
    if memory.priorities:
        pr_map = {
            "range": "tầm xa", "price": "giá rẻ", "comfort": "tiện nghi",
            "performance": "hiệu suất", "space": "không gian", "brand": "thương hiệu"
        }
        pr_str = ", ".join([pr_map.get(p, p) for p in memory.priorities])
        lines.append(f"- Ưu tiên: {pr_str}")
    if memory.daily_km:
        lines.append(f"- Quãng đường/ngày: ~{memory.daily_km} km")
    if memory.has_home_charging is not None:
        lines.append(f"- Sạc tại nhà: {'Có' if memory.has_home_charging else 'Không'}")
    if memory.mentioned_vehicles:
        lines.append(f"- Xe đã hỏi/quan tâm: {', '.join(memory.mentioned_vehicles).upper()}")
    if memory.rejected_vehicles:
        lines.append(f"- Xe không phù hợp (user đã nói): {', '.join(memory.rejected_vehicles).upper()}")
    if memory.last_recommended:
        lines.append(f"- Xe vừa được gợi ý: {', '.join(memory.last_recommended).upper()}")

    if len(lines) == 1:
        return ""  # Chưa có thông tin gì

    lines.append(f"\n⚠️ QUAN TRỌNG: KHÔNG hỏi lại những thông tin đã biết ở trên.")
    return "\n".join(lines)


def get_memory_display(memory: UserMemory) -> dict:
    """Tạo dict hiển thị memory trong sidebar (user-friendly)."""
    items = {}
    if memory.budget_vnd:
        items["💰 Ngân sách"] = f"{memory.budget_vnd/1_000_000:.0f} triệu"
    if memory.seats_needed:
        items["👥 Số chỗ"] = f"{memory.seats_needed} chỗ"
    if memory.family_size:
        items["👨‍👩‍👧 Gia đình"] = f"{memory.family_size} người"
    if memory.use_cases:
        uc_map = {"daily_city": "Đi phố", "family": "Gia đình",
                  "long_distance": "Đường dài", "business": "Kinh doanh"}
        items["🎯 Mục đích"] = ", ".join([uc_map.get(u, u) for u in memory.use_cases])
    if memory.priorities:
        pr_map = {"range": "Tầm xa", "price": "Giá tốt", "comfort": "Tiện nghi",
                  "performance": "Hiệu suất", "space": "Rộng rãi"}
        items["⭐ Ưu tiên"] = ", ".join([pr_map.get(p, p) for p in memory.priorities[:2]])
    if memory.last_recommended:
        items["🚗 Đã gợi ý"] = ", ".join([v.upper() for v in memory.last_recommended])
    return items
