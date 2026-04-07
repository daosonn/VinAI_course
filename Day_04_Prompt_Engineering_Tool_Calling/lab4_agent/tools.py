from langchain_core.tools import tool

# ===========================================================
# MOCK DATA — Dữ liệu giả lập hệ thống du lịch
# Lưu ý: Giá cả có logic (VD: cuối tuần đắt hơn, hạng cao hơn đắt hơn)
# Sinh viên cần đọc hiểu data để debug test cases.
# ===========================================================

FLIGHTS_DB = {
    ("Hà Nội", "Đà Nẵng"): [
        {"airline": "Vietnam Airlines", "departure": "06:00", "arrival": "07:20", "price": 1_450_000, "class": "economy"},
        {"airline": "Vietnam Airlines", "departure": "14:00", "arrival": "15:20", "price": 2_800_000, "class": "business"},
        {"airline": "VietJet Air",       "departure": "08:30", "arrival": "09:50", "price": 890_000,   "class": "economy"},
        {"airline": "Bamboo Airways",    "departure": "11:00", "arrival": "12:20", "price": 1_200_000, "class": "economy"},
    ],
    ("Hà Nội", "Phú Quốc"): [
        {"airline": "Vietnam Airlines", "departure": "07:00", "arrival": "09:15", "price": 2_100_000, "class": "economy"},
        {"airline": "VietJet Air",       "departure": "10:00", "arrival": "12:15", "price": 1_350_000, "class": "economy"},
        {"airline": "VietJet Air",       "departure": "16:00", "arrival": "18:15", "price": 1_100_000, "class": "economy"},
    ],
    ("Hà Nội", "Hồ Chí Minh"): [
        {"airline": "Vietnam Airlines", "departure": "06:00", "arrival": "08:10", "price": 1_600_000, "class": "economy"},
        {"airline": "VietJet Air",       "departure": "07:30", "arrival": "09:40", "price": 950_000,   "class": "economy"},
        {"airline": "Bamboo Airways",    "departure": "12:00", "arrival": "14:10", "price": 1_300_000, "class": "economy"},
        {"airline": "Vietnam Airlines", "departure": "18:00", "arrival": "20:10", "price": 3_200_000, "class": "business"},
    ],
    ("Hồ Chí Minh", "Đà Nẵng"): [
        {"airline": "Vietnam Airlines", "departure": "09:00", "arrival": "10:20", "price": 1_300_000, "class": "economy"},
        {"airline": "VietJet Air",       "departure": "13:00", "arrival": "14:20", "price": 780_000,   "class": "economy"},
    ],
    ("Hồ Chí Minh", "Phú Quốc"): [
        {"airline": "Vietnam Airlines", "departure": "08:00", "arrival": "09:00", "price": 1_100_000, "class": "economy"},
        {"airline": "VietJet Air",       "departure": "15:00", "arrival": "16:00", "price": 650_000,   "class": "economy"},
    ],
}

ATTRACTIONS_DB = {
    "Đà Nẵng": [
        {"name": "Bà Nà Hills",           "type": "Vui chơi",      "entry_fee": 850_000, "duration": "cả ngày",  "area": "Hòa Vang",  "rating": 4.6},
        {"name": "Cầu Vàng (Golden Bridge)", "type": "Check-in",   "entry_fee": 0,       "duration": "1-2 giờ",  "area": "Bà Nà",     "rating": 4.8},
        {"name": "Bãi biển Mỹ Khê",       "type": "Biển",          "entry_fee": 0,       "duration": "nửa ngày", "area": "Mỹ Khê",    "rating": 4.7},
        {"name": "Phố cổ Hội An",          "type": "Văn hóa",      "entry_fee": 120_000, "duration": "cả ngày",  "area": "Hội An",    "rating": 4.9},
        {"name": "Ngũ Hành Sơn",           "type": "Văn hóa",      "entry_fee": 40_000,  "duration": "2-3 giờ",  "area": "Ngũ Hành Sơn", "rating": 4.3},
        {"name": "Chợ Hàn",               "type": "Ẩm thực",       "entry_fee": 0,       "duration": "1-2 giờ",  "area": "Hải Châu",  "rating": 4.2},
    ],
    "Phú Quốc": [
        {"name": "Vinpearl Safari",        "type": "Vui chơi",      "entry_fee": 600_000, "duration": "cả ngày",  "area": "Bắc Đảo",   "rating": 4.5},
        {"name": "Bãi Sao",               "type": "Biển",           "entry_fee": 0,       "duration": "nửa ngày", "area": "An Thới",   "rating": 4.8},
        {"name": "Grand World Phú Quốc",   "type": "Vui chơi",      "entry_fee": 200_000, "duration": "cả ngày",  "area": "Bãi Dài",   "rating": 4.4},
        {"name": "Chợ đêm Dương Đông",    "type": "Ẩm thực",        "entry_fee": 0,       "duration": "2-3 giờ",  "area": "Dương Đông","rating": 4.3},
        {"name": "Hòn Thơm (cáp treo)",   "type": "Check-in",       "entry_fee": 750_000, "duration": "cả ngày",  "area": "An Thới",   "rating": 4.6},
        {"name": "Làng chài Hàm Ninh",    "type": "Văn hóa",        "entry_fee": 0,       "duration": "1-2 giờ",  "area": "Hàm Ninh", "rating": 4.1},
    ],
    "Hồ Chí Minh": [
        {"name": "Dinh Độc Lập",           "type": "Văn hóa",       "entry_fee": 40_000,  "duration": "1-2 giờ",  "area": "Quận 1",    "rating": 4.4},
        {"name": "Bến Nhà Rồng",           "type": "Văn hóa",       "entry_fee": 0,       "duration": "1 giờ",    "area": "Quận 4",    "rating": 4.2},
        {"name": "Phố đi bộ Nguyễn Huệ",  "type": "Check-in",      "entry_fee": 0,       "duration": "2-3 giờ",  "area": "Quận 1",    "rating": 4.5},
        {"name": "Chợ Bến Thành",          "type": "Ẩm thực",       "entry_fee": 0,       "duration": "2 giờ",    "area": "Quận 1",    "rating": 4.3},
        {"name": "Địa đạo Củ Chi",         "type": "Văn hóa",       "entry_fee": 70_000,  "duration": "cả ngày",  "area": "Củ Chi",    "rating": 4.6},
        {"name": "Landmark 81",            "type": "Check-in",      "entry_fee": 400_000, "duration": "1-2 giờ",  "area": "Bình Thạnh","rating": 4.5},
    ],
}

LOCAL_TRANSPORT_DB = {
    "Đà Nẵng": {
        "sân_bay_về_trung_tâm": {"grab_car": 80_000, "taxi": 120_000, "xe_buyt": 9_000},
        "di_chuyển_nội_thành":  {"grab_bike": 25_000, "grab_car": 45_000, "xe_máy_thuê": 150_000},
        "đi_hội_an":            {"grab_car": 250_000, "xe_buyt": 30_000, "thuê_xe_máy": 150_000},
    },
    "Phú Quốc": {
        "sân_bay_về_trung_tâm": {"grab_car": 150_000, "taxi": 200_000},
        "di_chuyển_nội_đảo":    {"xe_máy_thuê": 150_000, "grab_car": 80_000, "xe_điện": 50_000},
        "ra_đảo_hòn_thơm":      {"cáp_treo": 750_000, "tàu_cao_tốc": 200_000},
    },
    "Hồ Chí Minh": {
        "sân_bay_về_trung_tâm": {"grab_car": 120_000, "taxi": 180_000, "xe_buyt": 20_000, "metro": 20_000},
        "di_chuyển_nội_thành":  {"grab_bike": 20_000, "grab_car": 50_000, "xe_buyt": 7_000},
        "đi_củ_chi":            {"grab_car": 400_000, "xe_buyt": 20_000, "tour": 250_000},
    },
}

WEATHER_DB = {
    "Đà Nẵng": {
        1:  {"season": "Lạnh & mưa",   "temp": "18-22°C", "rain_chance": "cao",    "tip": "Mang áo khoác, ô. Biển sóng to, không nên bơi."},
        2:  {"season": "Lạnh & mưa",   "temp": "19-23°C", "rain_chance": "cao",    "tip": "Mang áo khoác, ô. Thích hợp tham quan phố cổ Hội An."},
        3:  {"season": "Mát mẻ",        "temp": "22-27°C", "rain_chance": "thấp",   "tip": "Thời tiết đẹp, bắt đầu mùa du lịch biển."},
        4:  {"season": "Nắng đẹp",      "temp": "25-30°C", "rain_chance": "rất thấp","tip": "Lý tưởng nhất để tắm biển. Mang kem chống nắng."},
        5:  {"season": "Nắng nóng",     "temp": "28-33°C", "rain_chance": "thấp",   "tip": "Rất nóng, nên ra biển sáng sớm hoặc chiều tối."},
        6:  {"season": "Nắng nóng",     "temp": "29-34°C", "rain_chance": "thấp",   "tip": "Mùa cao điểm du lịch, đặt phòng sớm. Đỉnh điểm nóng."},
        7:  {"season": "Nắng nóng",     "temp": "29-34°C", "rain_chance": "thấp",   "tip": "Tương tự tháng 6, mùa hè tuyệt vời."},
        8:  {"season": "Nắng & mưa rào","temp": "28-32°C", "rain_chance": "trung bình","tip": "Vẫn đẹp nhưng có mưa rào buổi chiều."},
        9:  {"season": "Mưa nhiều",     "temp": "25-29°C", "rain_chance": "cao",    "tip": "Bắt đầu mùa mưa, nên tránh thời điểm này."},
        10: {"season": "Mưa lớn",       "temp": "23-27°C", "rain_chance": "rất cao","tip": "Mùa bão, nguy hiểm. Không nên đi biển."},
        11: {"season": "Mưa & lạnh",    "temp": "21-25°C", "rain_chance": "cao",    "tip": "Mưa kéo dài, mang áo mưa và áo ấm."},
        12: {"season": "Lạnh & mưa",   "temp": "18-22°C", "rain_chance": "cao",    "tip": "Mang áo khoác dày. Thích hợp tham quan Hội An."},
    },
    "Phú Quốc": {
        1:  {"season": "Mùa khô",       "temp": "25-32°C", "rain_chance": "rất thấp","tip": "Đỉnh điểm đẹp nhất năm. Biển trong xanh, lặn biển tuyệt vời."},
        2:  {"season": "Mùa khô",       "temp": "25-32°C", "rain_chance": "rất thấp","tip": "Thời tiết hoàn hảo, mùa cao điểm. Đặt phòng sớm."},
        3:  {"season": "Mùa khô",       "temp": "26-33°C", "rain_chance": "thấp",   "tip": "Vẫn đẹp, bắt đầu nóng hơn."},
        4:  {"season": "Giao mùa",      "temp": "27-33°C", "rain_chance": "trung bình","tip": "Sóng bắt đầu nổi, hạn chế lặn biển xa bờ."},
        5:  {"season": "Đầu mùa mưa",  "temp": "26-31°C", "rain_chance": "cao",    "tip": "Mùa mưa bắt đầu, biển động. Giá phòng rẻ hơn 30-40%."},
        6:  {"season": "Mùa mưa",       "temp": "25-30°C", "rain_chance": "rất cao","tip": "Mưa nhiều, biển động mạnh. Chỉ nên đi nếu thích vắng."},
        7:  {"season": "Mùa mưa",       "temp": "25-30°C", "rain_chance": "rất cao","tip": "Tương tự tháng 6. Nhiều resort giảm giá sâu."},
        8:  {"season": "Mùa mưa",       "temp": "25-30°C", "rain_chance": "rất cao","tip": "Mưa lớn nhất trong năm. Nên chọn điểm đến khác."},
        9:  {"season": "Mùa mưa",       "temp": "25-30°C", "rain_chance": "cao",    "tip": "Vẫn còn mưa nhiều nhưng bắt đầu giảm."},
        10: {"season": "Giao mùa",      "temp": "25-31°C", "rain_chance": "trung bình","tip": "Thời tiết bắt đầu ổn định, biển đẹp dần."},
        11: {"season": "Mùa khô",       "temp": "25-31°C", "rain_chance": "thấp",   "tip": "Vào mùa đẹp, lý tưởng để đặt tour sớm."},
        12: {"season": "Mùa khô",       "temp": "25-31°C", "rain_chance": "rất thấp","tip": "Đẹp nhất, nhưng giá tăng cao dịp Tết. Đặt sớm 2-3 tháng."},
    },
    "Hồ Chí Minh": {
        1:  {"season": "Mùa khô",       "temp": "24-35°C", "rain_chance": "rất thấp","tip": "Nắng nóng, khô. Mang kem chống nắng và uống nhiều nước."},
        2:  {"season": "Mùa khô",       "temp": "25-35°C", "rain_chance": "rất thấp","tip": "Tiết trời đẹp, lý tưởng để tham quan."},
        3:  {"season": "Mùa khô",       "temp": "26-36°C", "rain_chance": "thấp",   "tip": "Nóng nhất trong năm. Ra ngoài sáng sớm hoặc chiều tối."},
        4:  {"season": "Giao mùa",      "temp": "26-35°C", "rain_chance": "trung bình","tip": "Nóng và bắt đầu có mưa rào buổi chiều."},
        5:  {"season": "Mùa mưa",       "temp": "25-33°C", "rain_chance": "cao",    "tip": "Mưa rào chiều tối, mang ô nhỏ theo."},
        6:  {"season": "Mùa mưa",       "temp": "24-32°C", "rain_chance": "cao",    "tip": "Mưa nhiều nhưng thường chỉ vài tiếng, không ảnh hưởng nhiều."},
        7:  {"season": "Mùa mưa",       "temp": "24-31°C", "rain_chance": "cao",    "tip": "Tương tự tháng 6, mang theo áo mưa."},
        8:  {"season": "Mùa mưa",       "temp": "24-31°C", "rain_chance": "cao",    "tip": "Mưa nhiều, đường hay ngập. Chú ý khi di chuyển."},
        9:  {"season": "Mùa mưa",       "temp": "24-31°C", "rain_chance": "rất cao","tip": "Mưa nhiều nhất, hay có ngập úng. Mang áo mưa."},
        10: {"season": "Mùa mưa",       "temp": "24-32°C", "rain_chance": "cao",    "tip": "Vẫn còn mưa nhiều."},
        11: {"season": "Giao mùa",      "temp": "24-33°C", "rain_chance": "trung bình","tip": "Bắt đầu vào mùa khô, thời tiết dễ chịu hơn."},
        12: {"season": "Mùa khô",       "temp": "24-34°C", "rain_chance": "thấp",   "tip": "Thời tiết đẹp, mùa cao điểm du lịch cuối năm."},
    },
}

HOTELS_DB = {
    "Đà Nẵng": [
        {"name": "Mường Thanh Luxury",   "stars": 5, "price_per_night": 1_800_000, "area": "Mỹ Khê",    "rating": 4.5},
        {"name": "Sala Danang Beach",     "stars": 4, "price_per_night": 1_200_000, "area": "Mỹ Khê",    "rating": 4.3},
        {"name": "Fivitel Danang",        "stars": 3, "price_per_night": 650_000,   "area": "Sơn Trà",   "rating": 4.1},
        {"name": "Memory Hostel",         "stars": 2, "price_per_night": 250_000,   "area": "Hải Châu",  "rating": 4.6},
        {"name": "Christina's Homestay", "stars": 2, "price_per_night": 350_000,   "area": "An Thượng", "rating": 4.7},
    ],
    "Phú Quốc": [
        {"name": "Vinpearl Resort",  "stars": 5, "price_per_night": 3_500_000, "area": "Bãi Dài",    "rating": 4.4},
        {"name": "Sol by Meliá",     "stars": 4, "price_per_night": 1_500_000, "area": "Bãi Trường", "rating": 4.2},
        {"name": "Lahana Resort",    "stars": 3, "price_per_night": 800_000,   "area": "Dương Đông", "rating": 4.0},
        {"name": "9Station Hostel",  "stars": 2, "price_per_night": 200_000,   "area": "Dương Đông", "rating": 4.5},
    ],
    "Hồ Chí Minh": [
        {"name": "Rex Hotel",        "stars": 5, "price_per_night": 2_800_000, "area": "Quận 1", "rating": 4.3},
        {"name": "Liberty Central",  "stars": 4, "price_per_night": 1_400_000, "area": "Quận 1", "rating": 4.1},
        {"name": "Cochin Zen Hotel", "stars": 3, "price_per_night": 550_000,   "area": "Quận 3", "rating": 4.4},
        {"name": "The Common Room",  "stars": 2, "price_per_night": 180_000,   "area": "Quận 1", "rating": 4.6},
    ],
}


@tool
def search_flights(origin: str, destination: str) -> str:
    """
    Tìm kiếm các chuyến bay giữa hai thành phố.
    Tham số:
    - origin: thành phố khởi hành (VD: 'Hà Nội', 'Hồ Chí Minh')
    - destination: thành phố đến (VD: 'Đà Nẵng', 'Phú Quốc')
    Trả về danh sách chuyến bay với hãng, giờ bay, giá vé.
    Nếu không tìm thấy tuyến bay, trả về thông báo không có chuyến.
    """
    try:
        # Tra cứu theo chiều thuận
        flights = FLIGHTS_DB.get((origin, destination))

        # Nếu không có, thử chiều ngược lại
        if not flights:
            flights = FLIGHTS_DB.get((destination, origin))
            if flights:
                # Đổi chiều: ghi chú là chuyến chiều ngược
                origin, destination = destination, origin

        if not flights:
            return f"Không tìm thấy chuyến bay từ {origin} đến {destination}. Hiện tại chỉ hỗ trợ các tuyến: Hà Nội↔Đà Nẵng, Hà Nội↔Phú Quốc, Hà Nội↔Hồ Chí Minh, Hồ Chí Minh↔Đà Nẵng, Hồ Chí Minh↔Phú Quốc."

        lines = [f"✈️ Chuyến bay từ {origin} đến {destination}:"]
        for i, f in enumerate(flights, 1):
            price_str = f"{f['price']:,}".replace(",", ".")
            lines.append(
                f"  {i}. {f['airline']} | {f['departure']} → {f['arrival']} | "
                f"{price_str}đ | Hạng {f['class']}"
            )
        return "\n".join(lines)

    except Exception as e:
        return f"Lỗi khi tìm kiếm chuyến bay: {str(e)}"


@tool
def search_hotels(city: str, max_price_per_night: int = 99_999_999) -> str:
    """
    Tìm kiếm khách sạn tại một thành phố, có thể lọc theo giá tối đa mỗi đêm.
    Tham số:
    - city: tên thành phố (VD: 'Đà Nẵng', 'Phú Quốc', 'Hồ Chí Minh')
    - max_price_per_night: giá tối đa mỗi đêm (VNĐ), mặc định không giới hạn
    Trả về danh sách khách sạn phù hợp với tên, số sao, giá, khu vực, rating.
    """
    try:
        hotels = HOTELS_DB.get(city)
        if not hotels:
            return f"Không tìm thấy khách sạn tại {city}. Hiện tại hỗ trợ: Đà Nẵng, Phú Quốc, Hồ Chí Minh."

        # Lọc theo giá tối đa
        filtered = [h for h in hotels if h["price_per_night"] <= max_price_per_night]

        if not filtered:
            max_price_str = f"{max_price_per_night:,}".replace(",", ".")
            return (
                f"Không tìm thấy khách sạn tại {city} với giá dưới {max_price_str}đ/đêm. "
                f"Hãy thử tăng ngân sách hoặc chọn thành phố khác."
            )

        # Sắp xếp theo rating giảm dần
        filtered.sort(key=lambda h: h["rating"], reverse=True)

        lines = [f"🏨 Khách sạn tại {city} (giá dưới {max_price_per_night:,}đ/đêm):".replace(",", ".")]
        for i, h in enumerate(filtered, 1):
            price_str = f"{h['price_per_night']:,}".replace(",", ".")
            stars = "⭐" * h["stars"]
            lines.append(
                f"  {i}. {h['name']} {stars} | {price_str}đ/đêm | "
                f"Khu vực: {h['area']} | Rating: {h['rating']}/5"
            )
        return "\n".join(lines)

    except Exception as e:
        return f"Lỗi khi tìm kiếm khách sạn: {str(e)}"


@tool
def calculate_budget(total_budget: int, expenses: str) -> str:
    """
    Tính toán ngân sách còn lại sau khi trừ các khoản chi phí.
    Tham số:
    - total_budget: tổng ngân sách ban đầu (VNĐ)
    - expenses: chuỗi mô tả các khoản chi, mỗi khoản cách nhau bởi dấu phẩy,
        định dạng 'tên_khoản:số_tiền' (VD: 'vé_máy_bay:890000,khách_sạn:650000')
    Trả về bảng chi tiết các khoản chi và số tiền còn lại.
    Nếu vượt ngân sách, cảnh báo rõ ràng số tiền thiếu.
    """
    try:
        # Parse chuỗi expenses thành dict {tên: số_tiền}
        expense_dict: dict[str, int] = {}
        for item in expenses.split(","):
            item = item.strip()
            if not item:
                continue
            if ":" not in item:
                return f"Lỗi định dạng: '{item}' không đúng dạng 'tên_khoản:số_tiền'. VD: 'vé_máy_bay:890000,khách_sạn:650000'"
            name, amount_str = item.split(":", 1)
            name = name.strip().replace("_", " ")
            amount_str = amount_str.strip()
            if not amount_str.isdigit():
                return f"Lỗi: số tiền '{amount_str}' không hợp lệ (phải là số nguyên dương)."
            expense_dict[name] = int(amount_str)

        if not expense_dict:
            return "Không có khoản chi nào được cung cấp."

        # Tính tổng chi phí
        total_expenses = sum(expense_dict.values())
        remaining = total_budget - total_expenses

        # Format bảng chi tiết
        budget_str = f"{total_budget:,}".replace(",", ".")
        total_exp_str = f"{total_expenses:,}".replace(",", ".")
        remaining_str = f"{abs(remaining):,}".replace(",", ".")

        lines = ["💰 Bảng chi phí:"]
        for name, amount in expense_dict.items():
            amount_str = f"{amount:,}".replace(",", ".")
            lines.append(f"  - {name.title()}: {amount_str}đ")
        lines.append("  ---")
        lines.append(f"  Tổng chi:    {total_exp_str}đ")
        lines.append(f"  Ngân sách:   {budget_str}đ")

        if remaining >= 0:
            lines.append(f"  Còn lại:     {remaining_str}đ ✅")
        else:
            lines.append(f"  THIẾU:       {remaining_str}đ ⚠️")
            lines.append(f"\n⚠️  Vượt ngân sách {remaining_str}đ! Cần điều chỉnh kế hoạch.")

        return "\n".join(lines)

    except Exception as e:
        return f"Lỗi khi tính ngân sách: {str(e)}"


@tool
def search_attractions(city: str, attraction_type: str = "tất cả") -> str:
    """
    Tìm kiếm địa điểm tham quan tại một thành phố.
    Tham số:
    - city: tên thành phố (VD: 'Đà Nẵng', 'Phú Quốc', 'Hồ Chí Minh')
    - attraction_type: loại địa điểm muốn lọc — 'Biển', 'Văn hóa', 'Vui chơi',
        'Check-in', 'Ẩm thực', hoặc 'tất cả' (mặc định)
    Trả về danh sách địa điểm với tên, loại, phí vào cửa, thời gian tham quan, rating.
    """
    try:
        attractions = ATTRACTIONS_DB.get(city)
        if not attractions:
            return f"Không tìm thấy địa điểm tham quan tại {city}. Hiện tại hỗ trợ: Đà Nẵng, Phú Quốc, Hồ Chí Minh."

        # Lọc theo loại nếu không phải "tất cả"
        if attraction_type != "tất cả":
            filtered = [a for a in attractions if a["type"].lower() == attraction_type.lower()]
            if not filtered:
                available_types = list({a["type"] for a in attractions})
                return (
                    f"Không tìm thấy địa điểm loại '{attraction_type}' tại {city}. "
                    f"Các loại hiện có: {', '.join(available_types)}."
                )
        else:
            filtered = attractions

        # Sắp xếp theo rating giảm dần
        filtered.sort(key=lambda a: a["rating"], reverse=True)

        lines = [f"🗺️ Địa điểm tham quan tại {city}:"]
        for i, a in enumerate(filtered, 1):
            fee_str = "Miễn phí" if a["entry_fee"] == 0 else f"{a['entry_fee']:,}đ/người".replace(",", ".")
            lines.append(
                f"  {i}. {a['name']} [{a['type']}] | Vào cửa: {fee_str} | "
                f"Thời gian: {a['duration']} | Khu vực: {a['area']} | Rating: {a['rating']}/5"
            )
        return "\n".join(lines)

    except Exception as e:
        return f"Lỗi khi tìm địa điểm tham quan: {str(e)}"


@tool
def estimate_local_transport(city: str, route: str = "sân_bay_về_trung_tâm") -> str:
    """
    Ước tính chi phí di chuyển nội địa tại một thành phố.
    Tham số:
    - city: tên thành phố (VD: 'Đà Nẵng', 'Phú Quốc', 'Hồ Chí Minh')
    - route: tuyến di chuyển cần ước tính. Các tuyến hỗ trợ:
        Đà Nẵng: 'sân_bay_về_trung_tâm', 'di_chuyển_nội_thành', 'đi_hội_an'
        Phú Quốc: 'sân_bay_về_trung_tâm', 'di_chuyển_nội_đảo', 'ra_đảo_hòn_thơm'
        Hồ Chí Minh: 'sân_bay_về_trung_tâm', 'di_chuyển_nội_thành', 'đi_củ_chi'
    Trả về bảng so sánh các phương tiện và giá tương ứng.
    """
    try:
        city_transport = LOCAL_TRANSPORT_DB.get(city)
        if not city_transport:
            return f"Không có thông tin di chuyển cho {city}. Hiện tại hỗ trợ: Đà Nẵng, Phú Quốc, Hồ Chí Minh."

        route_data = city_transport.get(route)
        if not route_data:
            available = list(city_transport.keys())
            return (
                f"Không tìm thấy tuyến '{route}' tại {city}. "
                f"Các tuyến hiện có: {', '.join(available)}."
            )

        route_display = route.replace("_", " ").title()
        lines = [f"🚗 Chi phí di chuyển tại {city} — {route_display}:"]
        for vehicle, price in sorted(route_data.items(), key=lambda x: x[1]):
            vehicle_display = vehicle.replace("_", " ").title()
            price_str = f"{price:,}".replace(",", ".")
            lines.append(f"  - {vehicle_display}: ~{price_str}đ")

        cheapest = min(route_data, key=route_data.get)
        lines.append(f"\n💡 Rẻ nhất: {cheapest.replace('_', ' ').title()} (~{route_data[cheapest]:,}đ)".replace(",", "."))
        return "\n".join(lines)

    except Exception as e:
        return f"Lỗi khi ước tính chi phí di chuyển: {str(e)}"


@tool
def get_weather_tips(city: str, month: int) -> str:
    """
    Lấy thông tin thời tiết và lời khuyên du lịch cho một thành phố theo tháng.
    Tham số:
    - city: tên thành phố (VD: 'Đà Nẵng', 'Phú Quốc', 'Hồ Chí Minh')
    - month: tháng trong năm (1-12)
    Trả về mùa, nhiệt độ, xác suất mưa, và lời khuyên cụ thể.
    """
    try:
        if not 1 <= month <= 12:
            return "Tháng không hợp lệ. Vui lòng nhập số từ 1 đến 12."

        city_weather = WEATHER_DB.get(city)
        if not city_weather:
            return f"Không có thông tin thời tiết cho {city}. Hiện tại hỗ trợ: Đà Nẵng, Phú Quốc, Hồ Chí Minh."

        w = city_weather[month]

        # Đánh giá tổng thể
        if w["rain_chance"] in ("rất thấp", "thấp"):
            overall = "✅ Thích hợp để du lịch"
        elif w["rain_chance"] == "trung bình":
            overall = "⚠️ Chấp nhận được, cần chuẩn bị"
        else:
            overall = "❌ Không lý tưởng, cân nhắc thời điểm khác"

        return (
            f"🌤️ Thời tiết {city} tháng {month}:\n"
            f"  Mùa:          {w['season']}\n"
            f"  Nhiệt độ:     {w['temp']}\n"
            f"  Khả năng mưa: {w['rain_chance']}\n"
            f"  Đánh giá:     {overall}\n"
            f"  💡 Lời khuyên: {w['tip']}"
        )

    except Exception as e:
        return f"Lỗi khi lấy thông tin thời tiết: {str(e)}"
