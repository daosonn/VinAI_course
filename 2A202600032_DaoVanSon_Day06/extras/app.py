"""
VinFast AI Car Advisor — MVP Prototype
Hackathon Day 6 | Kiến trúc 3 lớp + Conversation Memory
Chạy: streamlit run app.py
"""

import streamlit as st
import json, os, re
from pathlib import Path
from dataclasses import asdict

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

import sys
sys.path.append(str(Path(__file__).parent))

from services.router import route_intent, get_clarification_question, Intent
from services.recommender import recommend, get_vehicles_by_ids, format_vehicle_summary, get_vehicle_by_id
from services.faq_retriever import retrieve_faqs, format_faq_for_prompt, get_cta_for_faq
from services.llm_client import ask_llm, extract_preferences_from_conversation, load_prompt, summarize_user_context
from services.memory import UserMemory, update_memory, format_memory_for_prompt, get_memory_display

# ──────────────────────────────────────────────
# HELPER: Regex-based preference extraction (fallback khi LLM fail)
# ──────────────────────────────────────────────
def _extract_simple_preferences(text: str) -> dict:
    """Trích xuất ngân sách, số chỗ, mục đích dùng regex — fallback khi LLM unavailable."""
    # Bỏ qua nếu user đang phàn nàn/thắc mắc về bot
    if re.search(r'(tại sao|vì sao|sao|đâu có|không phải|chưa nói|nhầm)', text.lower()):
        return {}

    prefs = {}
    t = text.lower()

    # Budget: không giới hạn
    if re.search(r'(không giới hạn|k giới hạn|vô tư|tùy ý|không quan tâm giá|no limit|unlimited)', t):
        prefs["unlimited_budget"] = True
    else:
        # Budget: "400 triệu", "1.2 tỷ", "500tr", "khoảng 800 triệu", "1 tỷ 5"
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*(tỷ|ty|tỉ|ti)(?:\s*rưỡi|\s*ruoi|\s+([1-9]\d*))?\b', t)
        if m:
            base_val = float(m.group(1).replace(",", "."))
            extra = 0.0
            if "rưỡi" in m.group(0) or "ruoi" in m.group(0):
                extra = 0.5
            elif m.group(3):
                extra_str = m.group(3)
                if len(extra_str) == 1: extra_val = float(extra_str) * 100
                elif len(extra_str) == 2: extra_val = float(extra_str) * 10
                else: extra_val = float(extra_str[:3])
                extra = extra_val / 1000.0
            val = base_val + extra
            prefs["budget_vnd"] = int(val * 1_000_000_000)
            prefs["budget_note"] = f"khoảng {val} tỷ"
        else:
            m = re.search(r'(\d+(?:[.,]\d+)?)\s*(triệu|trieu|tr)\b', t)
            if m:
                val = float(m.group(1).replace(",", "."))
                prefs["budget_vnd"] = int(val * 1_000_000)
                prefs["budget_note"] = f"khoảng {int(val)} triệu"

    # Seats: "5 người", "7 chỗ", "gia đình 4 người"
    m = re.search(r'(\d+)\s*(người|nguoi|chỗ|cho|chổ)\b', t)
    if m:
        prefs["seats_needed"] = int(m.group(1))

    # Family size
    m = re.search(r'gia\s*(?:đình|dinh)\s*(\d+)\s*(?:người|nguoi)?', t)
    if m:
        prefs["family_size"] = int(m.group(1))
        if not prefs.get("seats_needed"):
            prefs["seats_needed"] = int(m.group(1))

    # Use cases
    use_cases = []
    if re.search(r'đi\s*phố|di\s*pho|nội\s*thành|noi\s*thanh|đi\s*làm|di\s*lam|hàng\s*ngày|hang\s*ngay', t):
        use_cases.append("daily_city")
    if re.search(r'gia\s*đình|gia\s*dinh|family|đưa\s*đón|dua\s*don', t):
        use_cases.append("family")
    if re.search(r'đường\s*dài|duong\s*dai|liên\s*tỉnh|lien\s*tinh|xa|đi\s*xa|di\s*xa', t):
        use_cases.append("long_distance")
    if use_cases:
        prefs["use_cases"] = use_cases

    # Priorities
    priorities = []
    if re.search(r'rẻ|re\b|tiết\s*kiệm|tiet\s*kiem|giá\s*tốt|gia\s*tot', t):
        priorities.append("price")
    if re.search(r'xa|tầm\s*xa|tam\s*xa|range', t):
        priorities.append("range")
    if re.search(r'tiện\s*nghi|tien\s*nghi|comfort|sang\s*trọng|sang\s*trong', t):
        priorities.append("comfort")
    if re.search(r'rộng|rong|không\s*gian|khong\s*gian|space', t):
        priorities.append("space")
    if priorities:
        prefs["priorities"] = priorities

    return prefs


def _detect_followup_type(messages: list) -> str | None:
    """Kiểm tra bot message trước đó có đang hỏi gì không → xác định loại follow-up."""
    if len(messages) < 2:
        return None
    # messages[-1] = user input vừa thêm, messages[-2] = bot message trước đó
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


# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="VinFast AI Advisor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ──────────────────────────────────────────────
# VINFAST BRAND CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Reset & Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* ── VinFast Color Variables ── */
:root {
    --vf-navy:    #002060;
    --vf-blue:    #1B4FBE;
    --vf-electric:#00A0E3;
    --vf-white:   #FFFFFF;
    --vf-light:   #F0F4FF;
    --vf-gray:    #6B7280;
    --vf-border:  #E5EAF5;
    --vf-dark:    #0D1B3E;
    --vf-cta:     #FF5722;
}

/* ── Streamlit main background ── */
.stApp {
    background: #F7F9FC;
}

/* ── Hide default streamlit header ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── HEADER BANNER ── */
.vf-header {
    background: linear-gradient(135deg, #002060 0%, #1B4FBE 60%, #00A0E3 100%);
    padding: 1.2rem 2rem;
    border-radius: 0 0 16px 16px;
    margin: -1rem -1rem 1.5rem -1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.vf-header-logo {
    font-size: 2rem;
    font-weight: 800;
    color: white;
    letter-spacing: -1px;
}
.vf-header-logo span { color: #00A0E3; }
.vf-header-sub {
    color: rgba(255,255,255,0.85);
    font-size: 0.85rem;
    font-weight: 400;
    margin-top: 2px;
}
.vf-header-badge {
    background: rgba(0,160,227,0.25);
    border: 1px solid rgba(0,160,227,0.5);
    color: #7DD3FC;
    font-size: 0.7rem;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 500;
    margin-left: auto;
}

/* ── CHAT CONTAINER ── */
.chat-container {
    max-width: 820px;
    margin: 0 auto;
}

/* ── USER BUBBLE ── */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: linear-gradient(135deg, #1B4FBE, #002060) !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 1rem 1.2rem !important;
    margin-left: 15% !important;
    margin-bottom: 0.75rem !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(0,32,96,0.2) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) * {
    color: white !important;
}

/* ── BOT BUBBLE ── */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: white !important;
    border-radius: 18px 18px 18px 4px !important;
    padding: 1rem 1.2rem !important;
    margin-right: 10% !important;
    margin-bottom: 0.75rem !important;
    border: 1px solid #E5EAF5 !important;
    box-shadow: 0 2px 12px rgba(0,32,96,0.08) !important;
}

/* ── CHAT INPUT ── */
.stChatInput > div {
    border: 2px solid #1B4FBE !important;
    border-radius: 12px !important;
    background: white !important;
    box-shadow: 0 2px 12px rgba(27,79,190,0.15) !important;
}
.stChatInput > div:focus-within {
    border-color: #00A0E3 !important;
    box-shadow: 0 0 0 3px rgba(0,160,227,0.2) !important;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1B3E 0%, #002060 100%) !important;
    border-right: 1px solid rgba(0,160,227,0.2) !important;
}
[data-testid="stSidebar"] * {
    color: rgba(255,255,255,0.9) !important;
}
[data-testid="stSidebar"] .stMarkdown a {
    color: #00A0E3 !important;
    text-decoration: none;
    font-weight: 500;
}
[data-testid="stSidebar"] .stMarkdown a:hover {
    color: #7DD3FC !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.15) !important;
}

/* ── SIDEBAR SECTION TITLE ── */
.sidebar-section {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: rgba(255,255,255,0.45) !important;
    margin: 1rem 0 0.5rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

/* ── MEMORY CARD ── */
.memory-card {
    background: rgba(0,160,227,0.12);
    border: 1px solid rgba(0,160,227,0.3);
    border-radius: 10px;
    padding: 0.75rem;
    margin: 0.5rem 0;
}
.memory-title {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #00A0E3 !important;
    margin-bottom: 0.5rem;
}
.memory-row {
    display: flex;
    gap: 0.4rem;
    align-items: center;
    padding: 2px 0;
    font-size: 0.78rem;
}
.memory-key { color: rgba(255,255,255,0.55) !important; min-width: 90px; }
.memory-val { color: white !important; font-weight: 500; }

/* ── CAR CHIP ── */
.car-chip {
    display: inline-block;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 0.75rem;
    margin: 2px;
    color: rgba(255,255,255,0.85) !important;
    transition: all 0.2s;
    text-decoration: none !important;
}
.car-chip:hover {
    background: rgba(0,160,227,0.25) !important;
    border-color: #00A0E3 !important;
    color: white !important;
}

/* ── QUICK ACTION BUTTONS (sidebar only) ── */
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 8px !important;
    color: rgba(255,255,255,0.9) !important;
    font-size: 0.8rem !important;
    padding: 0.4rem 0.8rem !important;
    width: 100% !important;
    text-align: left !important;
    transition: all 0.2s !important;
    font-weight: 400 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(0,160,227,0.25) !important;
    border-color: #00A0E3 !important;
    color: white !important;
}

/* ── SUGGESTION CHIP BUTTONS (main area) ── */
[data-testid="stMain"] .stButton > button {
    background: white !important;
    border: 1.5px solid #1B4FBE !important;
    border-radius: 20px !important;
    color: #1B4FBE !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 0.35rem 0.9rem !important;
    transition: all 0.2s !important;
    white-space: nowrap !important;
}
[data-testid="stMain"] .stButton > button:hover {
    background: #1B4FBE !important;
    color: white !important;
}

/* Reset button (red tint) */
[data-testid="stSidebar"] .stButton[data-testid*="reset"] > button {
    background: rgba(239,68,68,0.15) !important;
    border-color: rgba(239,68,68,0.3) !important;
}

/* ── LINK BUTTON (CTA) ── */
.stLinkButton > a {
    background: linear-gradient(135deg, #FF5722, #FF8A65) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.5rem 1.2rem !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    box-shadow: 0 3px 10px rgba(255,87,34,0.35) !important;
    transition: all 0.2s !important;
}
.stLinkButton > a:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 5px 15px rgba(255,87,34,0.45) !important;
}

/* ── SUGGESTION CHIPS ── */
.suggestion-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0.75rem 0 1rem 0;
}
.suggestion-chip {
    background: white;
    border: 1.5px solid #1B4FBE;
    color: #1B4FBE !important;
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
}
.suggestion-chip:hover {
    background: #1B4FBE;
    color: white !important;
}

/* ── STATUS BAR ── */
.status-bar {
    background: linear-gradient(90deg, #002060, #1B4FBE);
    border-radius: 8px;
    padding: 0.5rem 1rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.78rem;
    color: rgba(255,255,255,0.8) !important;
}
.status-dot {
    width: 8px; height: 8px;
    background: #4ADE80;
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 0 6px #4ADE80;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ── TURN COUNTER BADGE ── */
.turn-badge {
    background: rgba(0,160,227,0.15);
    border: 1px solid rgba(0,160,227,0.3);
    color: #00A0E3 !important;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.7rem;
    font-weight: 600;
}

/* ── HOTLINE PILL ── */
.hotline-pill {
    background: rgba(255,87,34,0.15);
    border: 1px solid rgba(255,87,34,0.3);
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
    margin-top: 0.5rem;
    font-size: 0.78rem;
    text-align: center;
}
.hotline-number {
    font-weight: 700;
    color: #FF8A65 !important;
    font-size: 0.9rem;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(27,79,190,0.3); border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# CACHE
# ──────────────────────────────────────────────
@st.cache_resource
def get_system_prompt():
    return load_prompt("system_prompt.txt")

@st.cache_resource
def get_cta_links():
    with open(Path(__file__).parent / "data" / "cta_links.json", encoding="utf-8") as f:
        return json.load(f)

# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "memory" not in st.session_state:
    st.session_state.memory = UserMemory()
if "conversation_context" not in st.session_state:
    st.session_state.conversation_context = []
if "pending_input" not in st.session_state:
    st.session_state.pending_input = None

# ──────────────────────────────────────────────
# API KEY CHECK
# ──────────────────────────────────────────────
api_key = os.getenv("GEMINI_API_KEY", "")
if not api_key:
    st.markdown("""
    <div class="vf-header">
        <div>
            <div class="vf-header-logo">Vin<span>Fast</span> ⚡</div>
            <div class="vf-header-sub">AI Car Advisor</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.warning("⚠️ Chưa có Gemini API Key. Lấy key miễn phí tại aistudio.google.com/apikey")
    k = st.text_input("Nhập Gemini API Key:", type="password", placeholder="AIzaSy...")
    if k:
        os.environ["GEMINI_API_KEY"] = k
        st.rerun()
    st.stop()

# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
cta_links = get_cta_links()
vehicle_urls = cta_links.get("vehicle_urls", {})
ctas = cta_links.get("ctas", {})

with st.sidebar:
    # Logo
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
        <div style="font-size:1.8rem; font-weight:800; color:white; letter-spacing:-1px;">
            Vin<span style="color:#00A0E3;">Fast</span>
        </div>
        <div style="font-size:0.7rem; color:rgba(255,255,255,0.5); letter-spacing:2px;
                    text-transform:uppercase; margin-top:2px;">AI Car Advisor</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Memory Panel ──
    memory = st.session_state.memory
    mem_display = get_memory_display(memory)

    st.markdown('<div class="sidebar-section">🧠 Chatbot đang nhớ</div>', unsafe_allow_html=True)

    if mem_display:
        rows_html = ""
        for k, v in mem_display.items():
            rows_html += f'<div class="memory-row"><span class="memory-key">{k}</span><span class="memory-val">{v}</span></div>'
        st.markdown(f"""
        <div class="memory-card">
            <div class="memory-title">⚡ Thông tin của bạn</div>
            {rows_html}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="font-size:0.78rem; color:rgba(255,255,255,0.4);
                    text-align:center; padding:0.75rem; font-style:italic;">
            Chưa có thông tin.<br>Hãy bắt đầu chat bên dưới.
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Dòng xe ──
    st.markdown('<div class="sidebar-section">🚗 Dòng xe VinFast</div>', unsafe_allow_html=True)
    cars = [
        ("VF 3", "vf3", "~527–579M"),
        ("VF 5 Plus", "vf5", "~458–479M"),
        ("VF 6", "vf6", "~675–765M"),
        ("VF 7", "vf7", "~1.185–1.251 tỷ"),
        ("VF 8", "vf8", "~1.211–1.243 tỷ"),
        ("VF 9", "vf9", "~1.633–2.181 tỷ"),
    ]
    chips_html = ""
    for name, vid, price in cars:
        url = vehicle_urls.get(vid, "#")
        chips_html += f'<a href="{url}" target="_blank" class="car-chip">{name}</a>'
    st.markdown(f'<div style="margin-top:0.4rem;">{chips_html}</div>', unsafe_allow_html=True)

    st.divider()

    # ── Quick Actions ──
    st.markdown('<div class="sidebar-section">⚡ Hành động nhanh</div>', unsafe_allow_html=True)

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        st.link_button("📅 Lái thử", ctas.get("test_drive_registration", {}).get("url", "#"), use_container_width=True)
        st.link_button("📍 Showroom", ctas.get("showroom_locator", {}).get("url", "#"), use_container_width=True)
    with btn_col2:
        st.link_button("🧮 Trả góp", ctas.get("installment_calculator", {}).get("url", "#"), use_container_width=True)
        st.link_button("⚡ Trạm sạc", ctas.get("charging_station_map", {}).get("url", "#"), use_container_width=True)

    st.divider()

    # ── Turn counter + Reset ──
    turn = st.session_state.memory.turn_count
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
        <span style="font-size:0.75rem; color:rgba(255,255,255,0.5);">Lượt hội thoại</span>
        <span class="turn-badge">{turn}</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🗑️ Xóa & bắt đầu lại"):
        st.session_state.messages = []
        st.session_state.memory = UserMemory()
        st.session_state.conversation_context = []
        st.rerun()

    # ── Hotline ──
    st.markdown("""
    <div class="hotline-pill">
        📞 Hotline 24/7<br>
        <span class="hotline-number">1900 23 23 89</span>
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# MAIN CHAT AREA
# ──────────────────────────────────────────────

# Header banner
st.markdown("""
<div class="vf-header">
    <div>
        <div class="vf-header-logo">Vin<span>Fast</span> ⚡</div>
        <div class="vf-header-sub">Tư vấn mua xe điện thông minh — Powered by Gemini AI</div>
    </div>
    <div class="vf-header-badge">🟢 AI đang hoạt động</div>
</div>
""", unsafe_allow_html=True)

# Status bar
st.markdown("""
<div class="status-bar">
    <div class="status-dot"></div>
    <span>Sẵn sàng tư vấn • Dữ liệu VF3 / VF5 / VF6 / VF7 / VF8 / VF9 • Không hallucinate thông số</span>
</div>
""", unsafe_allow_html=True)

# Welcome message
if not st.session_state.messages:
    welcome = (
        "Xin chào! Tôi là **VinFast AI Advisor** — trợ lý tư vấn mua xe điện. ⚡\n\n"
        "Tôi có thể giúp bạn:\n"
        "- 🚗 **Tư vấn xe phù hợp** theo ngân sách và nhu cầu\n"
        "- 📊 **So sánh** các mẫu VF3, VF5, VF6, VF7, VF8, VF9\n"
        "- 💡 **Giải đáp** về sạc điện, bảo hành, trả góp, lăn bánh\n"
        "- 📅 **Hướng dẫn** đăng ký lái thử & tìm showroom\n\n"
        "Bạn đang tìm loại xe như thế nào? _(Ví dụ: gia đình 5 người, ngân sách 1.2 tỷ, hay đi xa)_"
    )
    st.session_state.messages.append({"role": "assistant", "content": welcome})

# Suggestion chips (only when no conversation yet) — functional Streamlit buttons
if len(st.session_state.messages) <= 1:
    suggestions = [
        "🚗 Xe gia đình 5 người ~1.2 tỷ",
        "⚡ Xe đi phố ngân sách 500 triệu",
        "📊 So sánh VF8 và VF9",
        "💰 Tính trả góp VF8",
        "🔋 Sạc xe ở đâu?",
        "📅 Đăng ký lái thử",
    ]
    chip_cols = st.columns(3)
    for i, sug in enumerate(suggestions):
        if chip_cols[i % 3].button(sug, key=f"chip_{i}", use_container_width=True):
            st.session_state.pending_input = sug
            st.rerun()

# Display messages
for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "⚡"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg.get("cta"):
            cta = msg["cta"]
            st.link_button(f"👉 {cta['label']}", cta["url"])

# ──────────────────────────────────────────────
# CHAT INPUT
# ──────────────────────────────────────────────
user_input = st.chat_input(
    "Hỏi về xe VinFast... (VD: Gia đình 5 người, ngân sách 1.2 tỷ, hay đi xa)",
)

# Nhận input từ suggestion chip nếu có
if st.session_state.pending_input:
    user_input = st.session_state.pending_input
    st.session_state.pending_input = None

if user_input:
    st.session_state.memory.turn_count += 1

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)

    # ── PRE-ROUTING: Luôn trích xuất preferences bằng regex (không cần LLM) ──
    simple_prefs = _extract_simple_preferences(user_input)
    if simple_prefs:
        st.session_state.memory = update_memory(st.session_state.memory, simple_prefs)

    # ── FOLLOW-UP DETECTION: Kiểm tra user đang trả lời câu hỏi bot hỏi trước đó ──
    followup_type = _detect_followup_type(st.session_state.messages)

    # Intent routing
    intent_result = route_intent(user_input, st.session_state.conversation_context)
    intent = intent_result["intent"]

    # Nếu router trả UNCLEAR nhưng đây là follow-up trả lời bot → chuyển về RECOMMEND
    if intent == Intent.UNCLEAR and followup_type and simple_prefs:
        intent = Intent.RECOMMEND_VEHICLE
        intent_result["intent"] = intent
        intent_result["confidence"] = "medium"

    response_text = ""
    response_cta = None

    with st.spinner("⚡ Đang phân tích..."):
        # ── CẬP NHẬT TÓM TẮT NGỮ CẢNH LLM MỖI 2 TURN HOẶC THEO CÂU NGẮN ──
        if len(user_input) > 2:
            new_sum = summarize_user_context(user_input, st.session_state.memory.user_summary)
            if new_sum and new_sum != st.session_state.memory.user_summary:
                st.session_state.memory.user_summary = new_sum
        
        # Memory context string (inject vào mọi LLM call)
        mem_context = format_memory_for_prompt(st.session_state.memory)
        
        # Inject user_summary sâu hơn trực tiếp vào mem_context
        if st.session_state.memory.user_summary:
            mem_context += f"\n\n## GHI CHÚ ĐẶC BIỆT TỪ NGƯỜI DÙNG\n{st.session_state.memory.user_summary}"

        # ── INTERCEPTS ──
        unknown_vfs = list(set([f"VF {m}" for m in re.findall(r'\bvf\s*-?\s*(\d+)\b', user_input.lower()) if m not in {"3", "5", "6", "7", "8", "9"}]))
        if unknown_vfs:
            response_text = f"Hiện tại VinFast chưa có (hoặc tôi chưa có thông tin về) mẫu xe **{', '.join(unknown_vfs)}**.\n\nTôi có thể tư vấn cho bạn các dòng xe hiện tại: **VF 3, VF 5 Plus, VF 6, VF 7, VF 8, VF 9**. Bạn muốn tìm hiểu mẫu nào?"

        # ── HANDLERS ──
        elif intent == Intent.GREETING:
            response_text = get_clarification_question(intent_result)

        # H0b: Out of scope
        elif intent == Intent.OUT_OF_SCOPE:
            response_text = get_clarification_question(intent_result)

        # H1: Recommend
        elif intent == Intent.RECOMMEND_VEHICLE:
            # Thử LLM extraction cho context phong phú hơn
            conv_text = "\n".join([
                f"{m['role']}: {m['content']}"
                for m in st.session_state.messages[-10:]
            ])
            new_prefs = extract_preferences_from_conversation(conv_text)

            if new_prefs:
                st.session_state.memory = update_memory(st.session_state.memory, new_prefs)

            prefs = asdict(st.session_state.memory)

            # Kiểm tra đủ thông tin chưa (dùng memory trực tiếp, không phụ thuộc LLM confidence)
            has_budget = bool(st.session_state.memory.budget_vnd)
            has_seats = bool(st.session_state.memory.seats_needed)
            has_usecase = bool(st.session_state.memory.use_cases)
            info_score = sum([has_budget, has_seats, has_usecase])

            if info_score < 2:
                # Thiếu quá nhiều thông tin → hỏi thêm
                q = None
                if new_prefs and new_prefs.get("next_question"):
                    q = new_prefs["next_question"]
                if not q:
                    q = get_clarification_question(intent_result, prefs)
                response_text = q or "Bạn có thể cho tôi biết thêm về nhu cầu không?"
            else:
                # Đủ thông tin → recommend
                recs = recommend(prefs, top_n=3)
                if not recs:
                    response_text = (
                        "Tôi chưa tìm được mẫu xe hoàn toàn phù hợp với tiêu chí hiện tại.\n\n"
                        "Bạn thử điều chỉnh ngân sách hoặc liên hệ trực tiếp:\n"
                        "📞 Hotline **1900 23 23 89**"
                    )
                else:
                    st.session_state.memory.last_recommended = [r["vehicle"]["id"] for r in recs]
                    vehicles_summary = "\n\n---\n\n".join([
                        format_vehicle_summary(r["vehicle"])
                        + f"\nLý do phù hợp: {', '.join(r['reasons'][:3])}"
                        for r in recs
                    ])
                    full_context = mem_context + "\n\nXE GỢI Ý:\n" + vehicles_summary
                    prompt_tpl = load_prompt("recommendation.txt")
                    prompt = (prompt_tpl
                              .replace("{user_preferences}", json.dumps(prefs, ensure_ascii=False))
                              .replace("{recommended_vehicles}", vehicles_summary))
                    response_text = ask_llm(get_system_prompt(), prompt, full_context)
                    # Nếu LLM fail, tạo response thủ công từ data
                    if "sự cố kỹ thuật" in response_text or "Lỗi API" in response_text:
                        lines = ["Dựa trên nhu cầu của bạn, tôi gợi ý:\n"]
                        for i, r in enumerate(recs, 1):
                            v = r["vehicle"]
                            reasons_str = " | ".join(r["reasons"][:2]) if r["reasons"] else ""
                            lines.append(
                                f"**{i}. {v['name']}** — {v['price_display']}\n"
                                f"   {v['seats']} chỗ · {v['range_km']}km · {reasons_str}\n"
                            )
                        lines.append("_Bạn muốn tìm hiểu thêm về mẫu nào?_")
                        response_text = "\n".join(lines)
                    response_cta = {
                        "label": "📅 Đăng ký lái thử ngay",
                        "url": "https://shop.vinfastauto.com/vn_vi/dang-ky-lai-thu.html"
                    }

        elif intent == Intent.COMPARE_VEHICLES:
            mentioned = intent_result.get("mentioned_vehicles", [])
            for v in mentioned:
                if v not in st.session_state.memory.mentioned_vehicles:
                    st.session_state.memory.mentioned_vehicles.append(v)
            # Nếu người dùng không chỉ định xe, lấy ưu tiên từ danh sách vừa gợi ý (last_recommended)
            if len(mentioned) < 2:
                if st.session_state.memory.last_recommended and len(st.session_state.memory.last_recommended) >= 2:
                    mentioned = st.session_state.memory.last_recommended[:3] # Lấy tối đa 3 xe
                elif len(st.session_state.memory.mentioned_vehicles) >= 2:
                    mentioned = st.session_state.memory.mentioned_vehicles[-2:]

            if len(mentioned) < 2:
                response_text = "Bạn muốn so sánh mẫu xe nào? Ví dụ: **VF8 và VF9**, hoặc **VF6 và VF7**?"
            else:
                vehicles = get_vehicles_by_ids(mentioned)
                if len(vehicles) < 2:
                    response_text = f"Không tìm thấy đủ thông tin về: {', '.join(mentioned).upper()}. Thử lại không?"
                else:
                    v_data = "\n\n---\n\n".join([format_vehicle_summary(v) for v in vehicles])
                    prompt_tpl = load_prompt("comparison.txt")
                    prompt = (prompt_tpl
                              .replace("{vehicles_data}", v_data)
                              .replace("{user_criteria}",
                                       json.dumps(asdict(st.session_state.memory), ensure_ascii=False)))
                    llm_resp = ask_llm(get_system_prompt(), prompt, mem_context + "\n\n" + v_data)
                    # Nếu LLM fail, tạo bảng so sánh thủ công
                    if "sự cố kỹ thuật" in llm_resp or "Lỗi API" in llm_resp:
                        lines = [f"## So sánh {' vs '.join([v['name'] for v in vehicles])}\n"]
                        lines.append("| Tiêu chí | " + " | ".join([v['name'] for v in vehicles]) + " |")
                        lines.append("|" + "---|" * (len(vehicles) + 1))
                        lines.append("| Giá | " + " | ".join([v['price_display'] for v in vehicles]) + " |")
                        lines.append("| Chỗ ngồi | " + " | ".join([str(v['seats']) for v in vehicles]) + " |")
                        lines.append("| Quãng đường | " + " | ".join([f"{v['range_km']}km" for v in vehicles]) + " |")
                        lines.append("| Pin | " + " | ".join([f"{v.get('battery_kwh', '?')} kWh" for v in vehicles]) + " |")
                        lines.append("\n_Bạn quan tâm tiêu chí nào nhất?_")
                        response_text = "\n".join(lines)
                    else:
                        response_text = llm_resp
                    response_cta = {
                        "label": "📊 So sánh trên VinFast.com",
                        "url": "https://vinfastauto.com/vn_vi/so-sanh-xe"
                    }

        elif intent == Intent.ASK_VEHICLE_SPECS:
            mentioned = intent_result.get("mentioned_vehicles", [])
            for v in mentioned:
                if v not in st.session_state.memory.mentioned_vehicles:
                    st.session_state.memory.mentioned_vehicles.append(v)
            
            # Lấy xe gần nhất từ memory nếu không nhắc trong câu (nhưng có trong phiên làm việc)
            if not mentioned:
                if st.session_state.memory.last_recommended:
                    mentioned = [st.session_state.memory.last_recommended[0]]
                elif st.session_state.memory.mentioned_vehicles:
                    mentioned = [st.session_state.memory.mentioned_vehicles[-1]]

            if mentioned:
                # VF Wild chưa có trong dữ liệu sản phẩm
                if "vfwild" in mentioned:
                    response_text = (
                        "VinFast VF Wild hiện chưa có trong dữ liệu tôi đang quản lý.\n\n"
                        "Để biết thông tin mới nhất về VF Wild, vui lòng:\n"
                        "- 🌐 Xem tại [vinfastauto.com](https://vinfastauto.com/vn_vi)\n"
                        "- 📞 Hotline **1900 23 23 89**\n\n"
                        "Tôi có thể tư vấn cho bạn về VF3, VF5, VF6, VF7, VF8, VF9 ngay bây giờ."
                    )
                else:
                    vehicle = get_vehicle_by_id(mentioned[0])
                    if vehicle:
                        ctx = mem_context + f"\n\nTHÔNG TIN {vehicle['name']}:\n" + format_vehicle_summary(vehicle)
                        llm_resp = ask_llm(get_system_prompt(), f"Người dùng hỏi: {user_input}", ctx)
                        # Nếu LLM fail, hiển thị thông tin trực tiếp từ data
                        if "sự cố kỹ thuật" in llm_resp or "Lỗi API" in llm_resp:
                            v = vehicle
                            response_text = (
                                f"**{v['name']}** ({v.get('body_type', '')})\n\n"
                                f"- **Giá:** {v['price_display']}\n"
                                f"- **Chỗ ngồi:** {v['seats']} chỗ\n"
                                f"- **Quãng đường:** {v['range_km']} km\n"
                                f"- **Pin:** {v.get('battery_kwh', '?')} kWh ({v.get('battery_type', '')})\n"
                                f"- **Sạc nhanh DC:** {v.get('charging_dc_kw', '?')} kW\n"
                                f"- **Thời gian sạc nhanh:** {v.get('charging_time_fast', '?')}\n"
                                f"- **Bảo hành:** {v.get('warranty', 'N/A')}\n\n"
                                f"**Phù hợp:** {', '.join(v.get('suitable_for', [])[:3])}\n"
                                f"**Cân nhắc:** {v.get('tradeoffs', 'N/A')}\n\n"
                                f"_Bạn muốn biết thêm gì về {v['name']}?_"
                            )
                        else:
                            response_text = llm_resp
                        response_cta = {
                            "label": f"🔍 Xem chi tiết {vehicle['name']}",
                            "url": vehicle.get("official_url", "https://vinfastauto.com/vn_vi")
                        }
                    else:
                        response_text = "Tôi không có đủ thông tin về mẫu xe này. Xem tại [vinfastauto.com](https://vinfastauto.com/vn_vi)."
            else:
                response_text = "Bạn muốn hỏi thông số của mẫu xe nào? (VF3, VF5, VF6, VF7, VF8, VF9)"

        elif intent in [Intent.ASK_FAQ, Intent.ASK_FINANCING]:
            faqs = retrieve_faqs(user_input, top_n=2)
            if faqs:
                faq_ctx = mem_context + "\n\nFAQ LIÊN QUAN:\n" + format_faq_for_prompt(faqs)
                llm_resp = ask_llm(get_system_prompt(), user_input, faq_ctx)
                # Nếu LLM fail, hiển thị FAQ trực tiếp
                if "sự cố kỹ thuật" in llm_resp or "Lỗi API" in llm_resp:
                    response_text = format_faq_for_prompt(faqs)
                else:
                    response_text = llm_resp
                cta = get_cta_for_faq(faqs[0])
                if cta:
                    response_cta = cta
            else:
                response_text = (
                    "Câu hỏi này tôi chưa có đủ thông tin chính thức.\n\n"
                    "Vui lòng:\n"
                    "- 📞 Gọi hotline **1900 23 23 89** (24/7 miễn phí)\n"
                    "- 🌐 Xem [FAQ chính thức VinFast](https://vinfastauto.com/vn_vi/cau-hoi-thuong-gap)"
                )

        elif intent == Intent.ASK_TEST_DRIVE:
            response_text = (
                "Để đăng ký lái thử xe VinFast:\n"
                "1. **Online** — Điền form đăng ký trên website\n"
                "2. **Hotline** — Gọi 1900 23 23 89 để đặt lịch\n"
                "3. **Trực tiếp** — Đến showroom VinFast gần nhất\n\n"
                "_Sau khi đăng ký, VinFast sẽ xác nhận lịch qua email._\n\n"
                "Bạn muốn lái thử mẫu xe nào?"
            )
            response_cta = {
                "label": "📅 Đăng ký lái thử online",
                "url": "https://shop.vinfastauto.com/vn_vi/dang-ky-lai-thu.html"
            }

        elif intent == Intent.ASK_SHOWROOM:
            if "sạc" in user_input.lower() or "trạm" in user_input.lower():
                response_text = (
                    "Hệ thống trạm sạc VinFast (V-Green) phủ khắp toàn quốc:\n"
                    "- ✅ Có mặt trên **106+ quốc lộ**\n"
                    "- ✅ Trung tâm thương mại, chung cư, văn phòng\n"
                    "- ✅ App **EVCS.VN** — tìm trạm sạc theo thời gian thực\n\n"
                    "Khoảng cách giữa các trạm sạc DC trên trục chính < 100–150 km."
                )
                response_cta = {
                    "label": "⚡ Xem bản đồ trạm sạc",
                    "url": "https://vinfastauto.com/vn_vi/he-thong-tram-sac"
                }
            else:
                response_text = (
                    "VinFast có mạng lưới showroom, đại lý và trung tâm dịch vụ **trải rộng toàn quốc**.\n\n"
                    "Bạn có thể tìm showroom gần nhất trên website hoặc:\n"
                    "📞 **Hotline 24/7: 1900 23 23 89**"
                )
                response_cta = {
                    "label": "📍 Tìm showroom gần bạn",
                    "url": "https://vinfastauto.com/vn_vi"
                }

        elif intent == Intent.ASK_BUY:
            base_url = "https://shop.vinfastauto.com/vn_vi/dat-coc.html"
            lbl = "🛒 Đặt cọc ngay"
            mentioned = intent_result.get("mentioned_vehicles", [])
            # Lấy xe từ context nếu cần
            if not mentioned and st.session_state.memory.mentioned_vehicles:
                mentioned = [st.session_state.memory.mentioned_vehicles[-1]]
                
            if mentioned:
                v_id = mentioned[0]
                # Format url: dat-coc-xe-dien-vf5.html
                if v_id != "vfwild":
                    base_url = f"https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-{v_id}.html"
                    lbl = f"🛒 Đặt cọc {v_id.upper()}"

            response_text = (
                "Tuyệt vời! Bạn có thể tiến hành đặt cọc xe trực tuyến ngay trên website chính thức của VinFast.\n\n"
                "Tại đây, bạn cũng có thể chọn phiên bản, màu sắc và các tùy chọn bổ sung."
            )
            response_cta = {
                "label": lbl,
                "url": base_url
            }

        elif intent == Intent.CONTACT_HUMAN:
            response_text = (
                "Tôi là trợ lý ảo AI của VinFast. Nếu bạn muốn trao đổi trực tiếp với nhân viên tư vấn, vui lòng gọi điện đến hệ thống hotline của VinFast hoạt động 24/7.\n\n"
                "📞 **Hotline: 1900 23 23 89**"
            )

        elif intent == Intent.RECALL_MEMORY:
            mem_display = get_memory_display(st.session_state.memory)
            if mem_display:
                lines = ["Đây là những gì tôi đang nhớ về bạn:\n"]
                for k, v in mem_display.items():
                    lines.append(f"- {k}: **{v}**")
                lines.append("\nBạn muốn tôi tư vấn tiếp hay cần thay đổi thông tin gì?")
                response_text = "\n".join(lines)
            else:
                response_text = (
                    "Tôi chưa có thông tin gì về bạn. "
                    "Hãy cho tôi biết bạn đang tìm xe như thế nào? "
                    "(ngân sách, số người, mục đích sử dụng...)"
                )

        # UNCLEAR: xử lý thông minh hơn dựa trên context
        else:
            t_lower = user_input.lower()
            # Kiểm tra nếu user phàn nàn / gặp vấn đề
            if any(kw in t_lower for kw in ["không vào được", "lỗi", "hỏng", "broken", "error", "không hoạt động"]):
                response_text = (
                    "Xin lỗi vì sự bất tiện! Nếu link không hoạt động, bạn có thể:\n\n"
                    "- 🌐 Truy cập trực tiếp **[vinfastauto.com](https://vinfastauto.com/vn_vi)**\n"
                    "- 📞 Gọi hotline **1900 23 23 89** (24/7)\n\n"
                    "Tôi vẫn có thể tư vấn chọn xe, so sánh, hoặc giải đáp thắc mắc ngay tại đây."
                )
            # Nếu có follow-up data từ regex, xác nhận đã lưu
            elif simple_prefs and followup_type:
                mem_display = get_memory_display(st.session_state.memory)
                items = " · ".join([f"{k}: {v}" for k, v in mem_display.items()]) if mem_display else ""
                response_text = (
                    f"Đã ghi nhận! {items}\n\n"
                    "Bạn muốn tôi **gợi ý xe phù hợp** luôn, hay cần bổ sung thêm thông tin?"
                )
            else:
                clarify = get_clarification_question(intent_result, asdict(st.session_state.memory))
                response_text = clarify or (
                    "Tôi có thể giúp bạn:\n"
                    "- 🚗 **Tư vấn chọn xe** theo ngân sách & nhu cầu\n"
                    "- 📊 **So sánh** VF3 / VF5 / VF6 / VF7 / VF8 / VF9\n"
                    "- ⚡ **Thông tin sạc điện**, bảo hành, trả góp\n"
                    "- 📅 **Đăng ký lái thử** / tìm showroom\n\n"
                    "Bạn cần hỗ trợ gì?"
                )

    # ── Save & display response ──
    if not response_text:
        response_text = "Xin lỗi, có sự cố kỹ thuật. Vui lòng thử lại hoặc gọi **1900 23 23 89**."

    msg_data = {"role": "assistant", "content": response_text}
    if response_cta:
        msg_data["cta"] = response_cta

    st.session_state.messages.append(msg_data)
    st.session_state.conversation_context.append({"role": "user", "content": user_input})
    st.session_state.conversation_context.append({"role": "assistant", "content": response_text})

    st.rerun()  # Refresh để sidebar memory panel cập nhật

# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────
st.markdown("""
<div style="margin-top:2rem; padding:0.75rem 1rem; background:white; border-radius:10px;
            border:1px solid #E5EAF5; font-size:0.72rem; color:#9CA3AF; text-align:center;">
    ⚠️ Thông tin chỉ mang tính tham khảo. Giá và chính sách VinFast có thể thay đổi.
    Xác nhận tại <a href="https://vinfastauto.com/vn_vi" style="color:#1B4FBE;">vinfastauto.com</a>
    hoặc hotline <strong>1900 23 23 89</strong>.
</div>
""", unsafe_allow_html=True)
