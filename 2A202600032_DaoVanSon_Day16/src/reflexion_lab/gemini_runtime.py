from __future__ import annotations
import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv
from .schemas import QAExample, JudgeResult, ReflectionEntry
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM

load_dotenv()

# Cấu hình API Key của Google từ file .env
gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    
# Chọn model (gemini-2.5-flash là đủ nhanh và miễn phí cho loại bài học này)
# Nếu account đã được cấp quyền, có thể đổi thành gemini-2.5-pro 
model_name = "gemini-2.5-flash"

def count_tokens(text: str) -> int:
    try:
        model = genai.GenerativeModel(model_name)
        return model.count_tokens(text).total_tokens
    except Exception:
        return len(text.split()) # Dummy fallback

def _call_gemini(prompt: str, system_instruction: str, is_json: bool = False) -> tuple[str, int, int]:
    """Hàm gọi API Gemini thật, trả về (kết_quả_text, token_đã_dùng, thời_gian_chạy)"""
    start_time = time.time()
    try:
        # Trong cấu hình mới của genai, ta truyền system_instruction khi khởi tạo model
        generation_config = {"response_mime_type": "application/json"} if is_json else {}
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            generation_config=generation_config
        )
        
        response = model.generate_content(prompt)
        text_res = response.text
        # LLM trả về metadata về token (tuỳ bản SDK có thể lấy được hoặc không)
        # Giả lập nếu không lấy được
        tokens_used = 0
        if hasattr(response, 'usage_metadata'):
            tokens_used = getattr(response.usage_metadata, 'total_token_count', count_tokens(prompt + text_res))
        else:
            tokens_used = count_tokens(prompt + text_res)
            
    except Exception as e:
        text_res = "{}" if is_json else str(e)
        tokens_used = 0
        
    latency_ms = int((time.time() - start_time) * 1000)
    return text_res, tokens_used, latency_ms

def actor_answer(example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[str]) -> tuple[str, int, int]:
    prompt = f"Câu hỏi: {example.question}\n"
    if attempt_id > 1 and reflection_memory and agent_type == "reflexion":
        prompt += f"\nCHÚ Ý! Các bài học rút ra từ những lần giải sai trước:\n"
        for i, mem in enumerate(reflection_memory):
            prompt += f"- Lần {i+1}: {mem}\n"
            
    res, tokens, latency = _call_gemini(prompt, ACTOR_SYSTEM, is_json=False)
    return res.strip(), tokens, latency

def evaluator(example: QAExample, answer: str) -> tuple[JudgeResult, int, int]:
    prompt = f"Câu hỏi: {example.question}\nĐáp án đúng (Gold Answer): {example.gold_answer}\nCâu trả lời của AI AI: {answer}\n"
    
    res_str, tokens, latency = _call_gemini(prompt, EVALUATOR_SYSTEM, is_json=True)
    
    # Parse JSON
    try:
        data = json.loads(res_str)
        score = data.get("score", 0)
        reason = data.get("reason", "Lỗi Parse JSON")
    except Exception:
        score = 0
        reason = "Không thể parse JSON từ Giám khảo."
        
    return JudgeResult(score=score, reason=reason), tokens, latency

def reflector(example: QAExample, attempt_id: int, answer: str, judge: JudgeResult) -> tuple[ReflectionEntry, int, int]:
    prompt = f"Câu hỏi: {example.question}\nCâu trả lời bị chấm sai: {answer}\nNhận xét lỗi của Giám khảo: {judge.reason}\n"
    
    res_str, tokens, latency = _call_gemini(prompt, REFLECTOR_SYSTEM, is_json=True)
    
    try:
        data = json.loads(res_str)
        failure_reason = data.get("failure_reason", "")
        lesson = data.get("lesson", "")
        next_strategy = data.get("next_strategy", "")
    except Exception:
        failure_reason = "..."
        lesson = "..."
        next_strategy = "Hãy cẩn thận hơn."
        
    entry = ReflectionEntry(
        attempt_id=attempt_id,
        failure_reason=failure_reason,
        lesson=lesson,
        next_strategy=next_strategy
    )
    return entry, tokens, latency
