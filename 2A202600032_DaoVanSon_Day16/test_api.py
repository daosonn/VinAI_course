import os
from openai import OpenAI
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ Lỗi: Không tìm thấy OPENAI_API_KEY trong file .env hoặc biến môi trường.")
    exit(1)

print("✅ Đã tìm thấy API Key. Đang tiến hành gọi OpenAI (gpt-4o-mini)...")

try:
    # Khởi tạo client
    client = OpenAI(api_key=api_key)
    
    # Gửi một câu hỏi test đơn giản
    prompt = "Xin chào, bạn có nhận được tin nhắn này không? Hãy trả lời bằng tiếng Việt thật ngắn gọn trong 1 câu."
    print(f"👤 User: {prompt}")
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    print(f"🤖 OpenAI: {response.choices[0].message.content.strip()}")
    print("🎉 KẾT LUẬN: API CỦA BẠN ĐANG HOẠT ĐỘNG RẤT TỐT!")
    
except Exception as e:
    print(f"❌ Lỗi khi gọi API: {e}")
