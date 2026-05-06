from __future__ import annotations

import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from multi_memory_agent import MultiMemoryAgent, NoMemoryAgent


@dataclass
class Scenario:
    number: int
    name: str
    turns: list[str]
    expected_with_memory: str
    test_group: str


SCENARIOS = [
    Scenario(
        1,
        "Recall user name after filler turns",
        [
            "Tên tôi là Linh.",
            "Hôm nay trời đẹp.",
            "Tôi đang học Python.",
            "Cho tôi một lời khuyên học tập.",
            "Bây giờ đổi chủ đề sang Docker.",
            "Nhắc lại giúp tôi: tên tôi là gì?",
        ],
        "Linh",
        "profile recall",
    ),
    Scenario(
        2,
        "Allergy conflict update",
        [
            "Tôi dị ứng sữa bò.",
            "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.",
            "Vậy tôi dị ứng gì?",
        ],
        "đậu nành",
        "conflict update",
    ),
    Scenario(
        3,
        "Recall previous Docker debug episode",
        [
            "Hôm nay ta debug API Docker. Kết quả: lỗi do dùng localhost; cách đúng là dùng service name api. Bài học: trong Docker Compose hãy gọi service name.",
            "Mai tôi có một lỗi tương tự.",
            "Lần trước debug API Docker thì bài học chính là gì?",
        ],
        "service name",
        "episodic recall",
    ),
    Scenario(
        4,
        "Retrieve semantic memory chunk",
        [
            "Giải thích semantic memory retrieval là gì?",
        ],
        "semantic domain knowledge",
        "semantic retrieval",
    ),
    Scenario(
        5,
        "Recall preferred answer language",
        [
            "Trả lời bằng tiếng Việt nhé.",
            "Cho ví dụ đơn giản.",
            "Sau này nên dùng ngôn ngữ nào khi trả lời tôi?",
        ],
        "tiếng việt",
        "profile recall",
    ),
    Scenario(
        6,
        "Recall preferred style",
        [
            "Tôi muốn câu trả lời ngắn gọn.",
            "Giải thích API là gì.",
            "Phong cách trả lời kiểu nào tôi muốn?",
        ],
        "ngắn gọn",
        "profile recall",
    ),
    Scenario(
        7,
        "Context trim still preserves profile",
        [
            "Tên tôi là Minh.",
            "Turn filler 1: hãy nói về toán.",
            "Turn filler 2: hãy nói về văn.",
            "Turn filler 3: hãy nói về nhạc.",
            "Turn filler 4: hãy nói về phim.",
            "Turn filler 5: hãy nói về thể thao.",
            "Turn filler 6: hãy nói về lịch sử.",
            "Nhắc lại tên tôi là gì?",
        ],
        "Minh",
        "trim/token budget",
    ),
    Scenario(
        8,
        "Retrieve TTL privacy concept",
        [
            "TTL trong memory system dùng để làm gì?",
        ],
        "TTL policies",
        "semantic retrieval",
    ),
    Scenario(
        9,
        "Recall async teaching episode",
        [
            "Nhiệm vụ: giải thích async await cho người mới. Kết quả: ví dụ cooperative waiting giúp dễ hiểu. Bài học: dùng event loop analogy trước khi nói coroutine.",
            "Ta chuyển sang chủ đề khác một chút.",
            "Trước đây khi giải thích async await thì cách nào hiệu quả?",
        ],
        "cooperative waiting",
        "episodic recall",
    ),
    Scenario(
        10,
        "LangGraph state semantic retrieval",
        [
            "LangGraph memory state nên có các field nào?",
        ],
        "messages",
        "semantic retrieval",
    ),
]


def run_scenario(scenario: Scenario) -> dict[str, str | bool | int]:
    temp_dir = Path(tempfile.mkdtemp(prefix=f"memory_lab_{scenario.number}_"))
    try:
        with_memory = MultiMemoryAgent(storage_dir=temp_dir, memory_budget=900)
        no_memory = NoMemoryAgent()
        with_response = ""
        no_response = ""
        last_state = None
        for turn in scenario.turns:
            no_response = no_memory.answer(turn)
            with_response, last_state = with_memory.answer(turn)
        expected = scenario.expected_with_memory.lower()
        passed = expected in with_response.lower()
        prompt_chars = len(last_state["injected_prompt"]) if last_state else 0
        return {
            "number": scenario.number,
            "scenario": scenario.name,
            "group": scenario.test_group,
            "no_memory": no_response,
            "with_memory": with_response,
            "expected": scenario.expected_with_memory,
            "pass": passed,
            "prompt_chars": prompt_chars,
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_all() -> list[dict[str, str | bool | int]]:
    return [run_scenario(scenario) for scenario in SCENARIOS]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rows = run_all()
    passed = sum(1 for row in rows if row["pass"])
    print(f"Passed {passed}/{len(rows)} scenarios")
    print()
    print("| # | Scenario | Group | No-memory result | With-memory result | Pass? | Prompt chars |")
    print("|---|----------|-------|------------------|--------------------|-------|--------------|")
    for row in rows:
        no_memory = str(row["no_memory"]).replace("|", "/")
        with_memory = str(row["with_memory"]).replace("|", "/")
        status = "Pass" if row["pass"] else "Fail"
        print(
            f"| {row['number']} | {row['scenario']} | {row['group']} | "
            f"{no_memory} | {with_memory} | {status} | {row['prompt_chars']} |"
        )


if __name__ == "__main__":
    main()
