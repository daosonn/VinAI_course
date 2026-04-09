"""
Recommender Engine — Logic gợi ý xe dựa trên nhu cầu người dùng

Kiến trúc: Rule-based scoring + filter
- LLM KHÔNG chạy ở đây
- LLM chỉ dùng output của recommender để sinh explanation
- Source of truth = products.json
"""

import json
from functools import lru_cache
from pathlib import Path

# Load product data
DATA_PATH = Path(__file__).parent.parent / "data" / "products.json"


@lru_cache(maxsize=1)
def load_products():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def score_vehicle(vehicle: dict, preferences: dict) -> tuple[int, list[str]]:
    """
    Tính điểm phù hợp của một mẫu xe với nhu cầu người dùng.

    Returns:
        (score, reasons) — điểm số và lý do
    """
    score = 0
    reasons = []
    penalties = []

    budget = preferences.get("budget_vnd")
    seats_needed = preferences.get("seats_needed", 0) or 0
    use_cases = preferences.get("use_cases", []) or []
    priorities = preferences.get("priorities", []) or []
    daily_km = preferences.get("daily_km", 0) or 0

    price_from = vehicle.get("price_from", 0)
    price_to = vehicle.get("price_to", 0)
    seats = vehicle.get("seats", 0)
    range_km = vehicle.get("range_km", 0)

    # === HARD FILTERS (loại ngay nếu không đạt) ===

    # Filter 1: Ngân sách — giá cơ bản phải trong tầm
    if budget and price_from > budget * 1.1:  # cho phép 10% linh hoạt
        return -1, [f"Giá từ {price_from:,} VND vượt ngân sách {budget:,} VND"]

    # Filter 2: Số chỗ — phải đủ chỗ
    if seats_needed > 0 and seats < seats_needed:
        return -1, [f"Chỉ {seats} chỗ, cần ít nhất {seats_needed} chỗ"]

    # Filter 3: Quãng đường — nếu đi nhiều hàng ngày
    if daily_km > 0 and range_km > 0 and range_km < daily_km * 2:
        # Quãng đường < 2x nhu cầu hàng ngày — không an toàn
        penalties.append(-30)
        reasons.append(f"Quãng đường {range_km}km có thể chưa đủ cho {daily_km}km/ngày")

    # === SCORING (điểm tích cực) ===

    # Budget fit — giá phải tốt so với ngân sách
    if budget:
        if price_from <= budget * 0.85:
            score += 20  # Tiết kiệm hơn budget đáng kể
            reasons.append(f"Giá trong tầm ngân sách, tiết kiệm được {(budget - price_from):,.0f} VND")
        elif price_from <= budget:
            score += 15
            reasons.append("Giá phù hợp ngân sách")
        elif price_from <= budget * 1.1:
            score += 5
            reasons.append("Giá hơi vượt ngân sách nhẹ (khoảng 10%)")

    # Seat fit
    if seats_needed > 0:
        if seats >= seats_needed + 2:
            score += 10  # Bonus cho chỗ rộng rãi hơn
        elif seats >= seats_needed:
            score += 15  # Đúng nhu cầu

    # Use case match
    suitable_for = vehicle.get("suitable_for", [])
    suitable_text = " ".join(suitable_for).lower()

    if "daily_city" in use_cases:
        if "nội thành" in suitable_text or "đi làm" in suitable_text:
            score += 15
            reasons.append("Phù hợp đi phố hàng ngày")

    if "family" in use_cases:
        if "gia đình" in suitable_text:
            score += 15
            reasons.append("Phù hợp sử dụng gia đình")

    if "long_distance" in use_cases:
        if range_km >= 400:
            score += 20
            reasons.append(f"Quãng đường {range_km}km — phù hợp đường dài")
        elif range_km >= 300:
            score += 10

    # Priority match
    if "range" in priorities and range_km >= 400:
        score += 10
        reasons.append(f"Quãng đường tốt: {range_km}km")

    if "price" in priorities:
        segment = vehicle.get("segment", "")
        if segment in ["entry", "entry-mid"]:
            score += 10
            reasons.append("Phân khúc giá thấp hơn")

    if "space" in priorities and seats >= 7:
        score += 10
        reasons.append("7 chỗ — không gian rộng rãi")

    # Confidence penalty — MEDIUM/ASSUMPTION data ít điểm hơn
    if vehicle.get("price_confidence") == "ASSUMPTION":
        score = int(score * 0.8)
    elif vehicle.get("price_confidence") == "MEDIUM":
        score = int(score * 0.9)

    # Apply penalties
    for p in penalties:
        score += p

    return max(score, 0), reasons


def recommend(preferences: dict, top_n: int = 3) -> list[dict]:
    """
    Trả về danh sách xe được gợi ý xếp theo mức độ phù hợp.

    Args:
        preferences: Dict từ extract_preferences prompt
        top_n: Số xe tối đa trả về

    Returns:
        List[{vehicle_data, score, reasons}] đã sắp xếp theo score giảm dần
    """
    data = load_products()
    vehicles = data["vehicles"]

    scored = []
    for v in vehicles:
        score, reasons = score_vehicle(v, preferences)
        if score >= 0:  # -1 = hard filter loại bỏ
            scored.append({
                "vehicle": v,
                "score": score,
                "reasons": reasons
            })

    # Sắp xếp theo score giảm dần
    scored.sort(key=lambda x: x["score"], reverse=True)

    if not scored:
        max_seats = max(v.get("seats", 0) for v in vehicles)
        if preferences.get("seats_needed") and preferences["seats_needed"] > max_seats:
            largest = max(vehicles, key=lambda v: v.get("seats", 0))
            scored.append({
                "vehicle": largest,
                "score": 0,
                "reasons": [
                    f"Không có mẫu xe VinFast nào đủ {preferences['seats_needed']} chỗ. "
                    f"Mẫu có nhiều chỗ nhất là {largest['name']} ({largest['seats']} chỗ)."
                ],
                "over_budget": False,
            })
        elif preferences.get("budget_vnd"):
            cheapest = min(vehicles, key=lambda v: v.get("price_from", float("inf")))
            scored.append({
                "vehicle": cheapest,
                "score": 0,
                "reasons": [
                    f"Vượt ngân sách (giá từ {cheapest['price_from']:,.0f} VND, "
                    f"ngân sách {preferences['budget_vnd']:,.0f} VND) — "
                    f"đây là mẫu xe có giá thấp nhất của VinFast"
                ],
                "over_budget": True,
            })

    return scored[:top_n]


def get_vehicle_by_id(vehicle_id: str) -> dict | None:
    """Lấy thông tin chi tiết một mẫu xe theo ID."""
    data = load_products()
    for v in data["vehicles"]:
        if v["id"] == vehicle_id:
            return v
    return None


def get_vehicles_by_ids(vehicle_ids: list[str]) -> list[dict]:
    """Lấy thông tin nhiều mẫu xe theo danh sách ID."""
    return [v for v in [get_vehicle_by_id(vid) for vid in vehicle_ids] if v is not None]


def format_vehicle_summary(vehicle: dict) -> str:
    """Format thông tin xe để inject vào prompt — bao gồm pin và sạc."""
    confidence_note = ""
    if vehicle.get("price_confidence") in ["MEDIUM", "ASSUMPTION"]:
        confidence_note = " ⚠️ (cần xác minh tại showroom)"

    range_note = f" ({vehicle['range_note']})" if vehicle.get("range_note") else ""
    charging_ac = vehicle.get("charging_ac_kw", "N/A")
    charging_dc = vehicle.get("charging_dc_kw", "N/A")
    charging_fast = vehicle.get("charging_time_fast", "N/A")
    highlights = vehicle.get("highlights", [])
    highlights_str = "\n  - " + "\n  - ".join(highlights[:4]) if highlights else "N/A"

    return f"""
Xe: {vehicle['name']} ({vehicle.get('body_type', '')})
Giá: {vehicle['price_display']}{confidence_note}
Chỗ ngồi: {vehicle['seats']} chỗ
Quãng đường: {vehicle['range_km']} km{range_note}
Pin: {vehicle.get('battery_kwh', 'N/A')} kWh ({vehicle.get('battery_type', 'N/A')})
Sạc AC: {charging_ac} kW | Sạc DC nhanh: {charging_dc} kW
Thời gian sạc nhanh: {charging_fast}
Điểm nổi bật:{highlights_str}
Phù hợp với: {', '.join(vehicle.get('suitable_for', [])[:3])}
Không phù hợp: {', '.join(vehicle.get('not_suitable_for', [])[:2])}
Điểm cân nhắc: {vehicle.get('tradeoffs', 'N/A')}
Bảo hành: {vehicle.get('warranty', 'N/A')}
Link xem chi tiết: {vehicle.get('official_url', '#')}
""".strip()
