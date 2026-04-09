"""
LLM Client — Wrapper cho Google Gemini API (google-genai SDK mới)

Model: gemini-2.5-pro-preview-05-06
Note: "Gemini 3.1 Pro Preview" chưa tồn tại trong danh sách chính thức.
      Model Pro Preview mới nhất hiện tại là gemini-2.5-pro-preview-05-06.
      Cập nhật MODEL_ID bên dưới khi Google phát hành model mới hơn.
"""

import os
import json
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================
MODEL_ID = "gemini-2.0-flash"

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(filename: str) -> str:
    with open(PROMPTS_DIR / filename, "r", encoding="utf-8") as f:
        return f.read()


def _get_client():
    """Khởi tạo Gemini client với API key."""
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY chưa được cài đặt.")

    return genai.Client(api_key=api_key)


def ask_llm(
    system_prompt: str,
    user_message: str,
    context: str = "",
    conversation_history: list = None,
    temperature: float = 0.3,
    model: str = MODEL_ID
) -> str:
    """
    Gọi Gemini với system prompt và context data được inject.

    Args:
        system_prompt: System prompt (từ file prompts/)
        user_message: Tin nhắn người dùng
        context: Structured data (product / FAQ) inject vào — LLM chỉ dùng data này
        conversation_history: Lịch sử [{role, content}]
        temperature: 0.3 = ít hallucinate
        model: Model ID

    Returns:
        str: Phản hồi từ LLM
    """
    try:
        from google import genai
        from google.genai import types

        client = _get_client()

        # Build full system instruction với context
        full_system = system_prompt
        if context:
            full_system += (
                "\n\n## DỮ LIỆU THAM KHẢO\n"
                "Chỉ sử dụng thông tin dưới đây. KHÔNG tự tạo hoặc ước tính thêm.\n\n"
                + context
            )

        # Build contents từ history + message hiện tại
        contents = []
        if conversation_history:
            for turn in conversation_history[-6:]:
                role = "user" if turn["role"] == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part(text=turn["content"])]
                ))

        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=user_message)]
        ))

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=full_system,
                temperature=temperature,
                max_output_tokens=1024,
            )
        )

        return response.text

    except ValueError as e:
        return _fallback_response(str(e))
    except Exception as e:
        error_msg = str(e)
        # Model không tồn tại → gợi ý fallback
        if "not found" in error_msg.lower() or "404" in error_msg:
            return _fallback_response(
                f"Model '{model}' không khả dụng. "
                f"Thử đổi MODEL_ID sang 'gemini-2.0-flash' trong llm_client.py. Lỗi: {error_msg}"
            )
        return _fallback_response(f"Lỗi API: {error_msg}")


def extract_preferences_from_conversation(conversation_text: str) -> dict:
    """
    Dùng LLM trích xuất user preferences từ hội thoại → JSON.
    """
    try:
        from google import genai
        from google.genai import types

        client = _get_client()
        prompt_template = load_prompt("extract_preferences.txt")
        full_prompt = prompt_template.replace("{conversation}", conversation_text)

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=512,
            )
        )

        text = response.text.strip()

        # Clean JSON từ markdown code block nếu có
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    text = part
                    break

        return json.loads(text)

    except ValueError as e:
        print(f"Config error: {e}")
        return {}
    except json.JSONDecodeError:
        return {}
    except Exception as e:
        print(f"Error extracting preferences: {e}")
        return {}


def summarize_user_context(user_message: str, old_summary: str) -> str:
    """
    Dùng LLM tóm tắt các sở thích/ghét/thói quen của user (không thuộc specs chuẩn)
    và update vào user_summary.
    """
    try:
        from google import genai
        from google.genai import types

        client = _get_client()
        prompt = (
            "Bạn là một con AI phân tích Hội thoại Người - Hệ thống. "
            "Đây là tóm tắt cũ về người dùng (có thể rỗng): '{old_summary}'\n"
            "Câu nhắn mới nhất của họ: '{user_message}'\n\n"
            "Nếu câu nhắn mới có thông tin về thái độ, ngôn ngữ giao tiếp, "
            "xe họ cực thích/ghét mà không thể lưu bằng số liệu (ví dụ 'tôi thích vf3 quá', 'nói tiếng anh đi'), "
            "hãy bổ sung vào một câu mô tả ngắn gọn. "
            "Nếu không có thông tin gì đặc biệt, hãy trả về y hệt '{old_summary}'. "
            "CHỈ OUTPUT nội dung tóm tắt (hoàn toàn bằng Tiếng Việt), không giải thích."
        ).format(old_summary=old_summary.strip(), user_message=user_message.strip())

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=100,
            )
        )

        return response.text.strip()
    except Exception as e:
        print(f"Error summarizer: {e}")
        return old_summary


def _fallback_response(error_msg: str) -> str:
    # Ẩn chi tiết kỹ thuật khỏi user, log console an toàn (tránh UnicodeEncodeError trên Windows)
    try:
        print(f"[LLM ERROR] {error_msg}")
    except UnicodeEncodeError:
        print(f"[LLM ERROR] {error_msg.encode('ascii', 'replace').decode()}")
    return (
        "Xin lỗi, tôi đang gặp sự cố kỹ thuật. "
        "Vui lòng thử lại hoặc liên hệ hotline VinFast: **1900 23 23 89**."
    )
