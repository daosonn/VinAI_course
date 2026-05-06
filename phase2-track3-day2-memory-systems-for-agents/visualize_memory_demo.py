from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from multi_memory_agent import MultiMemoryAgent, normalize_words


STORAGE_DIR = Path("memory_store_demo")


def print_bar(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def print_section(title: str) -> None:
    print("\n" + "-" * 88)
    print(title)
    print("-" * 88)


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def pretty_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def show_route(state) -> None:
    print_section("0) LLM: câu trả lời đến từ API thật hay fallback")
    print(pretty_json(state.get("llm_info", {})))

    print_section("1) ROUTER: agent quyết định cần dùng memory nào")
    for memory_type, enabled in state["route"].items():
        mark = "ON " if enabled else "OFF"
        print(f"{mark} - {memory_type}")


def show_retrieval(state) -> None:
    print_section("2) RETRIEVE: data được lấy ra để chuẩn bị trả lời")
    print("Long-term profile retrieved:")
    print(pretty_json(state["user_profile"] or {}))

    print("\nEpisodic memories retrieved:")
    print(pretty_json(state["episodes"] or []))

    print("\nSemantic hits retrieved:")
    print(pretty_json(state["semantic_hits"] or []))

    print("\nRecent conversation retrieved:")
    print(pretty_json(state["recent_conversation"] or []))


def show_prompt_compaction(state) -> None:
    print_section("3) PROMPT + COMPACTION: memory được inject và trim như thế nào")
    prompt = state["injected_prompt"]
    budget = state["memory_budget"]
    print(f"memory_budget: {budget} characters")
    print(f"injected_prompt length: {len(prompt)} characters")
    print(f"budget status: {'OK, chưa vượt budget' if len(prompt) <= budget else 'VƯỢT budget'}")
    print("\nInjected prompt preview:")
    print(prompt)


def show_saved_files(agent: MultiMemoryAgent) -> None:
    print_section("4) SAVE: data hiện đang nằm trong file nào")
    profile_path = STORAGE_DIR / "profiles.json"
    episode_path = STORAGE_DIR / "episodes.json"
    print(f"Profile file: {profile_path}")
    print(pretty_json(load_json(profile_path, {})))
    print(f"\nEpisode file: {episode_path}")
    print(pretty_json(load_json(episode_path, [])))
    print("\nShort-term memory nằm trong RAM, không nằm trong file:")
    print(pretty_json(agent.short_term.messages))


def show_compact_rules(agent: MultiMemoryAgent) -> None:
    print_section("5) COMPACT RULES: hệ thống đang compact bằng cách nào")
    print(f"- Short-term sliding window giữ tối đa {agent.short_term.max_messages} messages gần nhất.")
    print("- Nếu quá giới hạn, message cũ nhất bị bỏ khỏi RAM.")
    print("- Profile memory compact bằng overwrite theo key: allergy cũ bị thay bằng allergy mới.")
    print(f"- Episodic memory giữ tối đa {agent.episodic.max_episodes} episodes mới nhất.")
    print("- Prompt compaction dùng memory_budget: nếu prompt dài quá thì giữ header và phần cuối.")


def show_keyword_math(query: str, state) -> None:
    print_section("6) KEYWORD MATCH: vì sao semantic/episodic retrieve được chunk này")
    query_words = normalize_words(query)
    print(f"Query words: {sorted(query_words)}")
    for hit in state["semantic_hits"]:
        doc_text = f"{hit['title']} {hit['text']} {' '.join(hit.get('tags', []))}"
        shared = sorted(query_words & normalize_words(doc_text))
        print(f"- Semantic hit `{hit['title']}` shared keywords: {shared}")
    for episode in state["episodes"]:
        episode_text = " ".join(
            [episode["task"], episode["trajectory"], episode["outcome"], episode["reflection"]]
        )
        shared = sorted(query_words & normalize_words(episode_text))
        print(f"- Episode `{episode['task']}` shared keywords: {shared}")
    if not state["semantic_hits"] and not state["episodes"]:
        print("Không có semantic hit hoặc episode hit trong lượt này.")


def run_turn(agent: MultiMemoryAgent, user_message: str) -> None:
    if "?" in user_message and not user_message.endswith("?"):
        print_section("ENCODING WARNING")
        print("Câu nhập có dấu ? ở giữa từ. Terminal có thể đang làm hỏng tiếng Việt.")
        print("Cách nhanh: dùng câu không dấu, ví dụ `Ten toi la Linh` hoặc chạy `chcp 65001` trước.")
    print_bar(f"USER: {user_message}")
    response, state = agent.answer(user_message)
    print(f"\nAGENT: {response}")
    show_route(state)
    show_retrieval(state)
    show_prompt_compaction(state)
    show_saved_files(agent)
    show_compact_rules(agent)
    show_keyword_math(user_message, state)


def reset_storage() -> None:
    if STORAGE_DIR.exists():
        shutil.rmtree(STORAGE_DIR)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def ensure_storage() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def run_scripted_demo() -> None:
    reset_storage()
    agent = MultiMemoryAgent(storage_dir=STORAGE_DIR, memory_budget=1200, use_llm=True)
    demo_turns = [
        "Tên tôi là Linh.",
        "Tôi dị ứng sữa bò.",
        "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.",
        "Nhiệm vụ: debug API Docker. Kết quả: lỗi do dùng localhost; cách đúng là dùng service name api. Bài học: trong Docker Compose hãy gọi service name.",
        "Lần trước debug API Docker thì bài học chính là gì?",
        "LangGraph memory state nên có các field nào?",
        "Nhắc lại tên tôi là gì?",
    ]
    for turn in demo_turns:
        run_turn(agent, turn)


def run_interactive() -> None:
    ensure_storage()
    agent = MultiMemoryAgent(storage_dir=STORAGE_DIR, memory_budget=1200, use_llm=True)
    print_bar("Interactive Multi-Memory Agent Visualizer")
    print("Gõ câu hỏi rồi Enter.")
    print("Lệnh đặc biệt: /reset để xóa memory demo, /exit để thoát.")
    print("Interactive mode KHÔNG tự reset memory khi mở lại. Dùng /reset nếu muốn xóa.")
    while True:
        try:
            user_message = input("\nBạn > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nThoát demo.")
            return
        if not user_message:
            continue
        if user_message == "/exit":
            print("Thoát demo.")
            return
        if user_message == "/reset":
            reset_storage()
            agent = MultiMemoryAgent(storage_dir=STORAGE_DIR, memory_budget=1200, use_llm=True)
            print("Đã reset memory demo.")
            continue
        run_turn(agent, user_message)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"
    if mode == "scripted":
        run_scripted_demo()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
