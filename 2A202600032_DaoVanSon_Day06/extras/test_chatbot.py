"""
TEST CHATBOT — Test toàn bộ logic chatbot offline (không cần Streamlit, không cần API key)

Chạy: python test_chatbot.py

Test các module:
1. Router: intent detection
2. Regex preference extraction
3. Follow-up detection
4. Recommender: vehicle scoring
5. FAQ retrieval
6. Memory management
7. Full conversation simulation (multi-turn)
8. Edge cases
"""

import sys
import os
import json
import re
from pathlib import Path
from dataclasses import asdict

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from services.router import route_intent, get_clarification_question, Intent, detect_mentioned_vehicles
from services.recommender import recommend, get_vehicle_by_id, get_vehicles_by_ids, format_vehicle_summary
from services.faq_retriever import retrieve_faqs, format_faq_for_prompt, detect_faq_category
from services.memory import UserMemory, update_memory, format_memory_for_prompt, get_memory_display

# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

PASS = 0
FAIL = 0
TOTAL = 0


def check(test_name: str, condition: bool, detail: str = ""):
    global PASS, FAIL, TOTAL
    TOTAL += 1
    if condition:
        PASS += 1
        print(f"  [PASS] {test_name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {test_name}")
        if detail:
            print(f"         -> {detail}")


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# Import regex extraction từ app.py (copy logic vì app.py dùng Streamlit)
def _extract_simple_preferences(text: str) -> dict:
    """Regex-based preference extraction — copy từ app.py để test offline."""
    prefs = {}
    t = text.lower()

    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(tỷ|ty|tỉ|ti)\b', t)
    if m:
        val = float(m.group(1).replace(",", "."))
        prefs["budget_vnd"] = int(val * 1_000_000_000)
        prefs["budget_note"] = f"khoảng {val} tỷ"
    else:
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*(triệu|trieu|tr)\b', t)
        if m:
            val = float(m.group(1).replace(",", "."))
            prefs["budget_vnd"] = int(val * 1_000_000)
            prefs["budget_note"] = f"khoảng {int(val)} triệu"

    m = re.search(r'(\d+)\s*(người|nguoi|chỗ|cho|chổ)\b', t)
    if m:
        prefs["seats_needed"] = int(m.group(1))

    m = re.search(r'gia\s*(?:đình|dinh)\s*(\d+)\s*(?:người|nguoi)?', t)
    if m:
        prefs["family_size"] = int(m.group(1))
        if not prefs.get("seats_needed"):
            prefs["seats_needed"] = int(m.group(1))

    use_cases = []
    if re.search(r'đi\s*phố|di\s*pho|nội\s*thành|noi\s*thanh|đi\s*làm|di\s*lam|hàng\s*ngày|hang\s*ngay', t):
        use_cases.append("daily_city")
    if re.search(r'gia\s*đình|gia\s*dinh|family|đưa\s*đón|dua\s*don', t):
        use_cases.append("family")
    if re.search(r'đường\s*dài|duong\s*dai|liên\s*tỉnh|lien\s*tinh|xa|đi\s*xa|di\s*xa', t):
        use_cases.append("long_distance")
    if use_cases:
        prefs["use_cases"] = use_cases

    priorities = []
    if re.search(r'rẻ|re\b|tiết\s*kiệm|tiet\s*kiem|giá\s*tốt|gia\s*tot', t):
        priorities.append("price")
    if re.search(r'tầm\s*xa|tam\s*xa|range', t):
        priorities.append("range")
    if re.search(r'tiện\s*nghi|tien\s*nghi|comfort|sang\s*trọng|sang\s*trong', t):
        priorities.append("comfort")
    if re.search(r'rộng|rong|không\s*gian|khong\s*gian|space', t):
        priorities.append("space")
    if priorities:
        prefs["priorities"] = priorities

    return prefs


def _detect_followup_type(messages: list) -> str:
    """Detect follow-up — copy từ app.py."""
    if len(messages) < 2:
        return None
    last_bot = messages[-2]
    if last_bot.get("role") != "assistant":
        return None
    bot_text = last_bot["content"].lower()
    if "ngân sách" in bot_text or "bao nhiêu" in bot_text:
        return "budget"
    if "mấy người" in bot_text or "số chỗ" in bot_text:
        return "seats"
    if "dùng xe để" in bot_text or "mục đích" in bot_text:
        return "use_case"
    return None


# ══════════════════════════════════════════════════════════
# TEST 1: ROUTER — INTENT DETECTION
# ══════════════════════════════════════════════════════════
section("TEST 1: ROUTER — INTENT DETECTION")

# Greeting
for msg in ["xin chào", "hello", "chào bạn", "hi", "chao"]:
    r = route_intent(msg)
    check(f"Greeting: '{msg}'", r["intent"] == Intent.GREETING,
          f"got {r['intent']}")

# Out of scope
for msg in ["chiến tranh trung đông", "bóng đá hôm nay", "bitcoin giá bao nhiêu"]:
    r = route_intent(msg)
    check(f"OutOfScope: '{msg}'", r["intent"] == Intent.OUT_OF_SCOPE,
          f"got {r['intent']}")

# Vehicle specs — nhắc 1 xe cụ thể
for msg, expected_v in [
    ("tôi muốn tư vấn xe vf3", ["vf3"]),
    ("cho tôi xem thông số VF8", ["vf8"]),
    ("VF 9 bao nhiêu tiền", ["vf9"]),
    ("vf5 plus có mấy chỗ", ["vf5"]),
]:
    r = route_intent(msg)
    check(f"Specs: '{msg}'",
          r["intent"] == Intent.ASK_VEHICLE_SPECS and r["mentioned_vehicles"] == expected_v,
          f"got {r['intent']}, vehicles={r['mentioned_vehicles']}")

# Compare — nhắc 2+ xe + keyword so sánh
for msg in ["so sánh vf3 và vf9", "vf8 vs vf9 cái nào tốt hơn", "so sanh vf6 vf7"]:
    r = route_intent(msg)
    check(f"Compare: '{msg}'",
          r["intent"] == Intent.COMPARE_VEHICLES and len(r["mentioned_vehicles"]) >= 2,
          f"got {r['intent']}, vehicles={r['mentioned_vehicles']}")

# Recommend — tín hiệu nhu cầu nhưng KHÔNG nhắc xe cụ thể
for msg in ["tôi muốn mua xe", "tư vấn xe cho gia đình", "xe nào phù hợp đi phố"]:
    r = route_intent(msg)
    check(f"Recommend: '{msg}'", r["intent"] == Intent.RECOMMEND_VEHICLE,
          f"got {r['intent']}")

# Test drive
for msg in ["đăng ký lái thử", "tôi muốn test drive", "lai thu xe"]:
    r = route_intent(msg)
    check(f"TestDrive: '{msg}'", r["intent"] == Intent.ASK_TEST_DRIVE,
          f"got {r['intent']}")

# Showroom
for msg in ["showroom ở đâu", "tìm đại lý gần nhất", "trạm sạc ở đâu"]:
    r = route_intent(msg)
    check(f"Showroom: '{msg}'", r["intent"] == Intent.ASK_SHOWROOM,
          f"got {r['intent']}")

# Financing
for msg in ["trả góp như thế nào", "tra gop vf8", "lãi suất bao nhiêu", "chi phí lăn bánh"]:
    r = route_intent(msg)
    check(f"Financing: '{msg}'", r["intent"] == Intent.ASK_FINANCING,
          f"got {r['intent']}")

# FAQ
for msg in ["bảo hành bao lâu", "chính sách bảo hành", "dịch vụ sau bán"]:
    r = route_intent(msg)
    check(f"FAQ: '{msg}'", r["intent"] == Intent.ASK_FAQ,
          f"got {r['intent']}")

# UNCLEAR — không match gì
for msg in ["ok", "hmm", "abc"]:
    r = route_intent(msg)
    check(f"Unclear: '{msg}'", r["intent"] == Intent.UNCLEAR,
          f"got {r['intent']}")


# ══════════════════════════════════════════════════════════
# TEST 2: REGEX PREFERENCE EXTRACTION
# ══════════════════════════════════════════════════════════
section("TEST 2: REGEX PREFERENCE EXTRACTION")

# Budget tests
tests_budget = [
    ("400 triệu", 400_000_000),
    ("khoảng 500 triệu", 500_000_000),
    ("1.2 tỷ", 1_200_000_000),
    ("2 tỷ", 2_000_000_000),
    ("800tr", 800_000_000),
    ("600 trieu", 600_000_000),
]
for text, expected in tests_budget:
    p = _extract_simple_preferences(text)
    check(f"Budget: '{text}' = {expected:,}",
          p.get("budget_vnd") == expected,
          f"got {p.get('budget_vnd')}")

# Seats tests
tests_seats = [
    ("5 người", 5),
    ("7 chỗ", 7),
    ("4 nguoi", 4),
]
for text, expected in tests_seats:
    p = _extract_simple_preferences(text)
    check(f"Seats: '{text}' = {expected}",
          p.get("seats_needed") == expected,
          f"got {p.get('seats_needed')}")

# Family size
p = _extract_simple_preferences("gia đình 5 người")
check("Family: 'gia đình 5 người'",
      p.get("family_size") == 5 and p.get("seats_needed") == 5,
      f"got family={p.get('family_size')}, seats={p.get('seats_needed')}")

# Use cases
tests_uc = [
    ("đi phố hàng ngày", ["daily_city"]),
    ("gia đình đi chơi", ["family"]),
    ("đường dài liên tỉnh", ["long_distance"]),
    ("gia dinh di pho", ["daily_city", "family"]),
]
for text, expected in tests_uc:
    p = _extract_simple_preferences(text)
    check(f"UseCase: '{text}'",
          p.get("use_cases") == expected,
          f"got {p.get('use_cases')}")

# Combined
p = _extract_simple_preferences("gia đình 5 người, ngân sách 1.2 tỷ, hay đi xa")
check("Combined: 'gia đình 5 người, ngân sách 1.2 tỷ, hay đi xa'",
      p.get("budget_vnd") == 1_200_000_000 and p.get("family_size") == 5 and "long_distance" in p.get("use_cases", []),
      f"got {p}")

# Empty
p = _extract_simple_preferences("xin chào")
check("Empty: 'xin chào' -> {}", p == {}, f"got {p}")


# ══════════════════════════════════════════════════════════
# TEST 3: FOLLOW-UP DETECTION
# ══════════════════════════════════════════════════════════
section("TEST 3: FOLLOW-UP DETECTION")

# Bot hỏi ngân sách, user trả "400 triệu"
msgs = [
    {"role": "assistant", "content": "Bạn dự kiến ngân sách khoảng bao nhiêu cho chiếc xe này?"},
    {"role": "user", "content": "400 triệu"},
]
check("Follow-up budget", _detect_followup_type(msgs) == "budget")

# Bot hỏi số người, user trả "5 người"
msgs = [
    {"role": "assistant", "content": "Gia đình bạn thường đi mấy người?"},
    {"role": "user", "content": "5 người"},
]
check("Follow-up seats", _detect_followup_type(msgs) == "seats")

# Không phải follow-up
msgs = [
    {"role": "assistant", "content": "Xin chào! Tôi có thể giúp gì?"},
    {"role": "user", "content": "hello"},
]
check("Not a follow-up", _detect_followup_type(msgs) is None)


# ══════════════════════════════════════════════════════════
# TEST 4: RECOMMENDER ENGINE
# ══════════════════════════════════════════════════════════
section("TEST 4: RECOMMENDER ENGINE")

# Test 1: Budget 500tr, 5 chỗ, đi phố
prefs1 = {"budget_vnd": 500_000_000, "seats_needed": 5, "use_cases": ["daily_city"]}
recs1 = recommend(prefs1, top_n=3)
check("Recommend: 500tr/5 chỗ/đi phố -> có kết quả", len(recs1) > 0,
      f"got {len(recs1)} results")
if recs1:
    top = recs1[0]["vehicle"]["id"]
    check(f"  Top pick is VF5 (giá phù hợp nhất)", top == "vf5",
          f"got {top}")

# Test 2: Budget 1.2 tỷ, 5 chỗ, gia đình + đường dài
prefs2 = {"budget_vnd": 1_200_000_000, "seats_needed": 5, "use_cases": ["family", "long_distance"]}
recs2 = recommend(prefs2, top_n=3)
check("Recommend: 1.2 tỷ/5 chỗ/gia đình+xa -> có kết quả", len(recs2) > 0)
if recs2:
    top_ids = [r["vehicle"]["id"] for r in recs2]
    check(f"  VF7 or VF8 in top picks", "vf7" in top_ids or "vf8" in top_ids,
          f"got {top_ids}")

# Test 3: Budget 400tr — VF3 dưới budget, VF5 gần budget
prefs3 = {"budget_vnd": 400_000_000, "seats_needed": 0, "use_cases": ["daily_city"]}
recs3 = recommend(prefs3, top_n=3)
check("Recommend: 400tr/đi phố -> có kết quả", len(recs3) > 0)
if recs3:
    top = recs3[0]["vehicle"]["id"]
    check(f"  Top pick: VF3 (cheapest)", top == "vf3", f"got {top}")

# Test 4: Budget quá thấp -> loại tất cả
prefs4 = {"budget_vnd": 100_000_000, "seats_needed": 0, "use_cases": []}
recs4 = recommend(prefs4, top_n=3)
check("Recommend: 100tr -> không tìm thấy xe", len(recs4) == 0,
      f"got {len(recs4)} results")

# Test 5: 7 chỗ — chỉ VF9
prefs5 = {"budget_vnd": 2_500_000_000, "seats_needed": 7, "use_cases": ["family"]}
recs5 = recommend(prefs5, top_n=3)
check("Recommend: 7 chỗ -> VF9", len(recs5) > 0)
if recs5:
    top = recs5[0]["vehicle"]["id"]
    check(f"  Top pick: VF9 (7 chỗ duy nhất)", top == "vf9", f"got {top}")

# Test: get_vehicle_by_id
v = get_vehicle_by_id("vf3")
check("get_vehicle_by_id('vf3')", v is not None and v["name"] == "VinFast VF 3")

v = get_vehicle_by_id("vfwild")
check("get_vehicle_by_id('vfwild') = None", v is None)

# Test: get_vehicles_by_ids
vs = get_vehicles_by_ids(["vf3", "vf9"])
check("get_vehicles_by_ids(['vf3','vf9'])", len(vs) == 2)

# Test: format_vehicle_summary includes battery info
v = get_vehicle_by_id("vf8")
summary = format_vehicle_summary(v)
check("format_vehicle_summary includes battery kWh", "kWh" in summary, f"missing kWh in summary")
check("format_vehicle_summary includes charging DC", "DC" in summary or "dc" in summary.lower())


# ══════════════════════════════════════════════════════════
# TEST 5: FAQ RETRIEVAL
# ══════════════════════════════════════════════════════════
section("TEST 5: FAQ RETRIEVAL")

# Basic FAQ queries
faqs = retrieve_faqs("trả góp như thế nào", top_n=2)
check("FAQ: 'trả góp' -> có kết quả", len(faqs) > 0)
if faqs:
    check("  Category is tai_chinh", faqs[0].get("category") == "tai_chinh",
          f"got category={faqs[0].get('category')}")

faqs = retrieve_faqs("bảo hành pin bao lâu", top_n=2)
check("FAQ: 'bảo hành pin' -> có kết quả", len(faqs) > 0)

faqs = retrieve_faqs("sạc ở đâu", top_n=2)
check("FAQ: 'sạc ở đâu' -> có kết quả", len(faqs) > 0)

# Không dấu
faqs = retrieve_faqs("tra gop nhu the nao", top_n=2)
check("FAQ (không dấu): 'tra gop' -> có kết quả", len(faqs) > 0,
      f"got {len(faqs)} results")

faqs = retrieve_faqs("bao hanh bao lau", top_n=2)
check("FAQ (không dấu): 'bao hanh' -> có kết quả", len(faqs) > 0,
      f"got {len(faqs)} results")

# Category detection
cats = detect_faq_category("trả góp lãi suất")
check("Category: 'trả góp lãi suất' -> tai_chinh", "tai_chinh" in cats, f"got {cats}")

cats = detect_faq_category("tra gop lai suat")
check("Category (không dấu): 'tra gop lai suat' -> tai_chinh", "tai_chinh" in cats, f"got {cats}")

cats = detect_faq_category("sạc tại nhà bao nhiêu tiền")
check("Category: 'sạc tại nhà' -> sac_dien", "sac_dien" in cats, f"got {cats}")


# ══════════════════════════════════════════════════════════
# TEST 6: MEMORY MANAGEMENT
# ══════════════════════════════════════════════════════════
section("TEST 6: MEMORY MANAGEMENT")

# Tạo memory mới
mem = UserMemory()
check("New memory: budget=None", mem.budget_vnd is None)
check("New memory: confidence=low", mem.confidence == "low")

# Update với budget
mem = update_memory(mem, {"budget_vnd": 500_000_000, "budget_note": "khoảng 500 triệu"})
check("After budget update: 500M", mem.budget_vnd == 500_000_000)

# Update với seats
mem = update_memory(mem, {"seats_needed": 5})
check("After seats update: 5", mem.seats_needed == 5)

# Update use_cases — merge test
mem = update_memory(mem, {"use_cases": ["daily_city"]})
check("Use cases after first: ['daily_city']", mem.use_cases == ["daily_city"])

mem = update_memory(mem, {"use_cases": ["family"]})
check("Use cases after merge: ['daily_city', 'family']",
      mem.use_cases == ["daily_city", "family"],
      f"got {mem.use_cases}")

mem = update_memory(mem, {"use_cases": ["daily_city"]})  # duplicate
check("Use cases no duplicate: still ['daily_city', 'family']",
      mem.use_cases == ["daily_city", "family"],
      f"got {mem.use_cases}")

# Format for prompt
prompt_ctx = format_memory_for_prompt(mem)
check("format_memory_for_prompt includes budget", "500" in prompt_ctx)
check("format_memory_for_prompt includes seats", "5 chỗ" in prompt_ctx)
check("format_memory_for_prompt includes 'KHÔNG hỏi lại'", "KHÔNG hỏi lại" in prompt_ctx)

# Display
display = get_memory_display(mem)
check("Memory display has budget", "Ngân sách" in str(display))
check("Memory display has seats", "Số chỗ" in str(display))


# ══════════════════════════════════════════════════════════
# TEST 7: FULL CONVERSATION SIMULATION
# ══════════════════════════════════════════════════════════
section("TEST 7: FULL CONVERSATION SIMULATION")

def simulate_conversation(turns: list[str], description: str):
    """Simulate multi-turn conversation and show results."""
    print(f"\n  --- Scenario: {description} ---")
    memory = UserMemory()
    messages = []
    messages.append({"role": "assistant", "content": "Xin chào! Tôi có thể giúp gì?"})

    for user_msg in turns:
        # Pre-routing: extract preferences
        simple_prefs = _extract_simple_preferences(user_msg)
        if simple_prefs:
            memory = update_memory(memory, simple_prefs)

        messages.append({"role": "user", "content": user_msg})

        # Follow-up detection
        followup = _detect_followup_type(messages)

        # Route
        result = route_intent(user_msg)
        intent = result["intent"]

        # Override UNCLEAR if follow-up
        if intent == Intent.UNCLEAR and followup and simple_prefs:
            intent = Intent.RECOMMEND_VEHICLE

        # Determine response
        response = ""
        if intent == Intent.GREETING:
            response = "[GREETING] Xin chào! Tôi giúp gì?"
        elif intent == Intent.OUT_OF_SCOPE:
            response = "[OUT_OF_SCOPE] Tôi chỉ hỗ trợ về xe VinFast."
        elif intent == Intent.ASK_VEHICLE_SPECS:
            mentioned = result["mentioned_vehicles"]
            if mentioned:
                v = get_vehicle_by_id(mentioned[0])
                if v:
                    response = f"[SPECS] {v['name']}: {v['price_display']}, {v['seats']} chỗ, {v['range_km']}km"
                else:
                    response = f"[SPECS] Không có data cho {mentioned[0]}"
            else:
                response = "[SPECS] Bạn hỏi xe nào?"
        elif intent == Intent.COMPARE_VEHICLES:
            mentioned = result["mentioned_vehicles"]
            if len(mentioned) >= 2:
                vs = get_vehicles_by_ids(mentioned)
                names = [v["name"] for v in vs]
                response = f"[COMPARE] So sánh: {' vs '.join(names)}"
            else:
                response = "[COMPARE] Cần ít nhất 2 xe để so sánh."
        elif intent == Intent.RECOMMEND_VEHICLE:
            prefs = asdict(memory)
            has_budget = bool(memory.budget_vnd)
            has_seats = bool(memory.seats_needed)
            has_uc = bool(memory.use_cases)
            info_score = sum([has_budget, has_seats, has_uc])
            if info_score < 2:
                q = get_clarification_question(result, prefs)
                response = f"[RECOMMEND/ASK] {q}"
            else:
                recs = recommend(prefs, top_n=3)
                if recs:
                    names = [r["vehicle"]["name"] for r in recs]
                    response = f"[RECOMMEND] Top picks: {', '.join(names)}"
                else:
                    response = "[RECOMMEND] Không tìm thấy xe phù hợp."
        elif intent == Intent.ASK_FINANCING:
            faqs = retrieve_faqs(user_msg, top_n=1)
            if faqs:
                response = f"[FAQ/FINANCE] {faqs[0]['question'][:60]}..."
            else:
                response = "[FAQ/FINANCE] Chưa có thông tin."
        elif intent == Intent.ASK_FAQ:
            faqs = retrieve_faqs(user_msg, top_n=1)
            if faqs:
                response = f"[FAQ] {faqs[0]['question'][:60]}..."
            else:
                response = "[FAQ] Chưa có thông tin."
        elif intent == Intent.ASK_TEST_DRIVE:
            response = "[TEST_DRIVE] Hướng dẫn đăng ký lái thử."
        elif intent == Intent.ASK_SHOWROOM:
            response = "[SHOWROOM] Tìm showroom/trạm sạc."
        else:
            t_lower = user_msg.lower()
            if any(kw in t_lower for kw in ["nhớ", "nho", "biết tôi", "biet toi"]):
                mem_disp = get_memory_display(memory)
                response = f"[MEMORY] Tôi nhớ: {mem_disp}"
            elif any(kw in t_lower for kw in ["không vào được", "lỗi", "hỏng"]):
                response = "[COMPLAINT] Xin lỗi! Thử vinfastauto.com hoặc hotline."
            elif simple_prefs and followup:
                response = f"[FOLLOWUP] Đã ghi nhận: {simple_prefs}"
            else:
                response = f"[UNCLEAR] Bạn cần hỗ trợ gì?"

        messages.append({"role": "assistant", "content": response})

        # Print turn
        mem_short = get_memory_display(memory)
        mem_str = " | ".join([f"{k}={v}" for k, v in mem_short.items()]) if mem_short else "(empty)"
        print(f"    User: {user_msg}")
        print(f"    Bot:  {response}")
        print(f"    Mem:  {mem_str}")
        print()

    return memory


# Scenario 1: Happy path — đầy đủ thông tin ngay
print()
mem = simulate_conversation([
    "gia đình 5 người, ngân sách 1.2 tỷ, hay đi xa",
], "Happy path: full info in 1 message")
check("S1: budget extracted", mem.budget_vnd == 1_200_000_000)
check("S1: seats extracted", mem.seats_needed == 5)
check("S1: use_case extracted", "long_distance" in mem.use_cases)

# Scenario 2: Multi-turn — thông tin dần dần
print()
mem = simulate_conversation([
    "tôi muốn mua xe",
    "ngân sách khoảng 800 triệu",
    "5 người",
    "đi phố hàng ngày",
], "Multi-turn: gradual info")
check("S2: budget=800M", mem.budget_vnd == 800_000_000)
check("S2: seats=5", mem.seats_needed == 5)
check("S2: use_case=daily_city", "daily_city" in mem.use_cases)

# Scenario 3: Hỏi xe cụ thể
print()
simulate_conversation([
    "tôi muốn tư vấn xe vf3",
    "vf3 sạc bao lâu",
], "Specific vehicle: VF3")

# Scenario 4: So sánh
print()
simulate_conversation([
    "so sánh vf3 và vf9",
], "Compare: VF3 vs VF9")

# Scenario 5: Greeting + out of scope + recover
print()
simulate_conversation([
    "xin chào",
    "thời tiết hôm nay thế nào",
    "à mà tôi muốn mua xe, 1 tỷ, 5 người",
], "Greeting + OOS + Recover")

# Scenario 6: Không dấu
print()
mem = simulate_conversation([
    "toi muon mua xe",
    "500 trieu",
    "4 nguoi",
], "Không dấu: toi muon mua xe")
check("S6: budget=500M", mem.budget_vnd == 500_000_000)
check("S6: seats=4", mem.seats_needed == 4)

# Scenario 7: Follow-up answers
print()
mem = simulate_conversation([
    "tư vấn xe cho tôi",
    "1.2 tỷ",
    "5 người",
    "gia đình đi xa",
], "Follow-up: answer bot questions step by step")
check("S7: budget=1.2B", mem.budget_vnd == 1_200_000_000)
check("S7: seats=5", mem.seats_needed == 5)
check("S7: use_cases has family + long_distance",
      "family" in mem.use_cases and "long_distance" in mem.use_cases,
      f"got {mem.use_cases}")

# Scenario 8: Memory question
print()
simulate_conversation([
    "gia đình 4 người, 600 triệu",
    "bạn có nhớ tôi là ai không",
], "Memory question after providing info")

# Scenario 9: Complaint
print()
simulate_conversation([
    "link của bạn đưa tôi không vào được",
], "User complaint about broken link")

# Scenario 10: Code-switch Việt/Anh
print()
simulate_conversation([
    "I want to buy a car, budget around 1 tỷ, family 5 người",
], "Code-switch Vietnamese + English")

# Scenario 11: Edge — quá ngắn
print()
simulate_conversation([
    "ok",
    "hmm",
    "???",
], "Edge: very short messages")

# Scenario 12: Trả góp / FAQ
print()
simulate_conversation([
    "trả góp VF8 như thế nào",
    "bảo hành pin bao lâu",
    "sạc ở đâu",
], "FAQ flow: financing, warranty, charging")

# Scenario 13: Lái thử + Showroom
print()
simulate_conversation([
    "đăng ký lái thử",
    "showroom ở Hà Nội",
], "Test drive + Showroom")

# Scenario 14: Đổi chủ đề đột ngột
print()
simulate_conversation([
    "tôi muốn mua xe 1 tỷ",
    "sạc ở đâu vậy",
    "quay lại, tư vấn xe cho tôi đi",
], "Topic switch mid-conversation")

# Scenario 15: VF Wild
print()
simulate_conversation([
    "thông số VF Wild",
], "VF Wild (not in product data)")


# ══════════════════════════════════════════════════════════
# TEST 8: EDGE CASES
# ══════════════════════════════════════════════════════════
section("TEST 8: EDGE CASES")

# Empty string
r = route_intent("")
check("Empty input -> UNCLEAR", r["intent"] == Intent.UNCLEAR)

# Very long input
long_msg = "tôi muốn mua xe " * 100
r = route_intent(long_msg)
check("Very long input -> still routes", r["intent"] == Intent.RECOMMEND_VEHICLE)

# Special characters
r = route_intent("!!!@@@###$$$")
check("Special chars -> UNCLEAR", r["intent"] == Intent.UNCLEAR)

# Number only
p = _extract_simple_preferences("500")
check("'500' alone -> no budget (no unit)", p.get("budget_vnd") is None)

# Mixed number + unit
p = _extract_simple_preferences("khoảng 1,5 tỷ")
check("'1,5 tỷ' -> 1.5B", p.get("budget_vnd") == 1_500_000_000,
      f"got {p.get('budget_vnd')}")

# Vehicle detection edge
vs = detect_mentioned_vehicles("VF-8 và VF 9")
check("Vehicle detect: 'VF-8 và VF 9'", "vf8" in vs and "vf9" in vs, f"got {vs}")

vs = detect_mentioned_vehicles("vf5 plus")
check("Vehicle detect: 'vf5 plus'", "vf5" in vs, f"got {vs}")

# Greeting + vehicle = NOT greeting
r = route_intent("chào bạn, cho tôi xem VF8")
check("'chào + VF8' -> SPECS not GREETING", r["intent"] == Intent.ASK_VEHICLE_SPECS,
      f"got {r['intent']}")


# ══════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════
section("SUMMARY")
print(f"\n  Total:  {TOTAL}")
print(f"  Passed: {PASS}")
print(f"  Failed: {FAIL}")
print(f"  Rate:   {PASS/TOTAL*100:.1f}%")
print()

if FAIL == 0:
    print("  ALL TESTS PASSED!")
else:
    print(f"  {FAIL} test(s) FAILED — review above.")

print()
