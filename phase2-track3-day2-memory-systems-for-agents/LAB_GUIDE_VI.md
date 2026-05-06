# Hướng dẫn Lab 17 - Multi-Memory Agent

## 1. Bài lab yêu cầu gì?

Bài lab yêu cầu xây một agent có bộ nhớ. Agent bình thường chỉ thấy prompt hiện tại, nên khi qua nhiều lượt hoặc qua session mới thì nó dễ "quên". Lab này yêu cầu ta làm agent biết lấy lại thông tin quan trọng từ nhiều loại memory.

Các deliverable chính:

- Source code agent.
- Data files cho semantic memory.
- `BENCHMARK.md` so sánh no-memory và with-memory trên 10 hội thoại nhiều lượt.
- Reflection về privacy, deletion, limitation.

## 2. Ý tưởng dễ hiểu

Hãy tưởng tượng agent có 4 cuốn sổ:

| Loại memory | Ví dụ đời thường | Trong code |
|---|---|---|
| Short-term | Nhớ vài câu vừa nói trong cuộc trò chuyện hiện tại | `ShortTermMemory` |
| Long-term profile | Hồ sơ người dùng: tên, sở thích, dị ứng | `LongTermProfileMemory` |
| Episodic | Nhật ký kinh nghiệm: lần trước debug lỗi gì, cách nào hiệu quả | `EpisodicMemory` |
| Semantic | Sách kiến thức/domain docs | `SemanticMemory` |

Nếu gom tất cả vào một chuỗi text lớn thì rất khó quản lý. Vì vậy bài tốt cần tách từng memory ra thành backend/interface riêng.

## 3. Các file đã tạo

| File | Vai trò |
|---|---|
| `multi_memory_agent.py` | Code chính của agent và các memory backend |
| `data/domain_docs.json` | Kho kiến thức semantic dạng JSON |
| `benchmark.py` | Script chạy 10 test conversations |
| `BENCHMARK.md` | Báo cáo kết quả benchmark và reflection |
| `LAB_GUIDE_VI.md` | File giải thích này |

## 4. Luồng hoạt động của agent

Khi user gửi một câu, agent chạy theo flow:

1. Tạo `MemoryState`.
2. Router đọc câu hỏi và đoán cần memory nào.
3. `retrieve_memory()` lấy thông tin từ các backend phù hợp.
4. `build_memory_prompt()` nhét memory vào prompt theo section rõ ràng.
5. Agent tạo câu trả lời.
6. `save_memory()` lưu lại fact mới hoặc episode mới nếu có.

Trong code, `MemoryState` có các field quan trọng:

```python
class MemoryState(TypedDict):
    messages: list
    user_profile: dict
    episodes: list[dict]
    semantic_hits: list[dict]
    memory_budget: int
```

Đây là phần giống LangGraph: state đi qua nhiều node/function.

## 5. Giải thích từng memory

### Short-term memory

Short-term memory lưu vài lượt gần nhất. Nó giống RAM: nhanh, tạm thời, nhưng có giới hạn.

Trong code:

```python
self.messages = self.messages[-self.max_messages :]
```

Dòng này nghĩa là nếu conversation quá dài, chỉ giữ lại `max_messages` tin nhắn cuối.

### Long-term profile memory

Long-term profile lưu thông tin cá nhân bền vững hơn, ví dụ:

- Tên người dùng
- Dị ứng
- Ngôn ngữ muốn dùng
- Phong cách trả lời

Backend hiện tại là JSON file. Trong production có thể thay bằng Redis.

Điểm quan trọng: nếu user sửa thông tin cũ, fact mới thắng.

Ví dụ bắt buộc của lab:

```text
Tôi dị ứng sữa bò.
À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.
```

Kết quả đúng:

```text
allergy = đậu nành
```

### Episodic memory

Episodic memory lưu kinh nghiệm theo dạng:

- Task
- Trajectory
- Outcome
- Reflection

Ví dụ:

```text
Task: debug API Docker
Outcome: lỗi do dùng localhost; cách đúng là dùng service name api
Reflection: trong Docker Compose hãy gọi service name
```

Lần sau user hỏi "lần trước debug API thì bài học là gì?", agent lấy lại episode này.

### Semantic memory

Semantic memory lưu kiến thức chung, ví dụ docs về:

- Agent memory types
- Context budget
- Privacy
- LangGraph memory flow
- Docker Compose debugging

Trong production thường dùng Chroma/FAISS vector search. Trong bài này dùng keyword search fallback để chạy offline.

## 6. Router làm gì?

Router quyết định câu hỏi nên lấy memory nào.

Ví dụ:

- Câu có "tên", "dị ứng", "phong cách" -> profile memory.
- Câu có "lần trước", "debug", "trước đây" -> episodic memory.
- Câu có "TTL", "context", "semantic", "LangGraph" -> semantic memory.

Nhờ router, agent không nhét toàn bộ memory vào prompt. Nó chỉ lấy phần liên quan, giúp tiết kiệm context.

## 7. Prompt injection là gì?

Prompt injection ở đây không phải tấn công bảo mật. Ý nghĩa trong lab là: lấy memory đã retrieve rồi đưa vào prompt cho model thấy.

Prompt có section rõ:

```text
Long-term profile: ...
Episodic memories: ...
Semantic knowledge: ...
Recent conversation: ...
```

Nếu không inject vào prompt, model không thể dùng memory dù backend có lưu dữ liệu.

## 8. Context budget / trim

Context window có giới hạn. Bài này dùng `memory_budget` tính bằng character count thay cho token count.

Trong benchmark dùng:

```python
memory_budget = 900
```

Nếu prompt dài hơn budget, code sẽ trim để không vượt quá giới hạn.

## 9. Cách chạy

Chạy benchmark:

```bash
python benchmark.py
```

Kết quả kỳ vọng:

```text
Passed 10/10 scenarios
```

Nếu muốn tự demo trong Python:

```python
from multi_memory_agent import MultiMemoryAgent

agent = MultiMemoryAgent()
print(agent.answer("Tên tôi là Linh.")[0])
print(agent.answer("Nhắc lại tên tôi là gì?")[0])
```

Chạy visualizer với API thật:

```bash
python visualize_memory_demo.py
```

Visualizer sẽ dùng `OPENAI_API_KEY` trong `.env`. Nếu muốn ép dùng OpenAI, đặt:

```text
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini
```

Mỗi lượt hỏi sẽ hiện:

- LLM provider/model thật đang dùng.
- Router bật memory nào.
- Data retrieve được từ profile/episode/semantic memory.
- Prompt đã inject memory.
- File JSON đang lưu profile/episode.
- Cách compact bằng sliding window và memory budget.

## 10. Khi bị hỏi demo nên giải thích thế nào?

Bạn có thể nói:

"Em tách memory thành 4 backend. Short-term dùng sliding window cho hội thoại gần đây. Long-term profile dùng JSON key-value để lưu facts như tên, dị ứng, style. Episodic memory lưu task, trajectory, outcome, reflection. Semantic memory dùng JSON docs và keyword retrieval làm fallback cho Chroma/FAISS. Khi user hỏi, router chọn backend phù hợp, retrieve memory vào `MemoryState`, rồi inject vào prompt theo section. Sau khi trả lời, agent update profile hoặc lưu episode. Benchmark gồm 10 multi-turn conversations và so sánh với baseline no-memory."

## 11. Điểm cần nhớ để đạt rubric

- Có đủ 4 memory types.
- Mỗi memory có interface riêng, không gom thành một blob.
- Có `MemoryState`.
- Có `retrieve_memory(state)`.
- Có router.
- Có prompt section rõ ràng.
- Có save/update memory.
- Có conflict handling.
- Có benchmark 10 conversations.
- Có reflection privacy/limitations.
