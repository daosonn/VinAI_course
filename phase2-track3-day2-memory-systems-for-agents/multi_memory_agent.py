from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_words(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9_\-]+|[\w]+", text.lower(), flags=re.UNICODE)
    stop_words = {
        "toi",
        "tôi",
        "minh",
        "mình",
        "la",
        "là",
        "va",
        "và",
        "cho",
        "cua",
        "của",
        "the",
        "a",
        "an",
        "is",
        "to",
        "in",
    }
    return {word for word in words if len(word) > 1 and word not in stop_words}


def overlap_score(query: str, text: str) -> int:
    return len(normalize_words(query) & normalize_words(text))


def deaccent_vietnamese(text: str) -> str:
    replacements = {
        "à": "a",
        "á": "a",
        "ạ": "a",
        "ả": "a",
        "ã": "a",
        "â": "a",
        "ầ": "a",
        "ấ": "a",
        "ậ": "a",
        "ẩ": "a",
        "ẫ": "a",
        "ă": "a",
        "ằ": "a",
        "ắ": "a",
        "ặ": "a",
        "ẳ": "a",
        "ẵ": "a",
        "è": "e",
        "é": "e",
        "ẹ": "e",
        "ẻ": "e",
        "ẽ": "e",
        "ê": "e",
        "ề": "e",
        "ế": "e",
        "ệ": "e",
        "ể": "e",
        "ễ": "e",
        "ì": "i",
        "í": "i",
        "ị": "i",
        "ỉ": "i",
        "ĩ": "i",
        "ò": "o",
        "ó": "o",
        "ọ": "o",
        "ỏ": "o",
        "õ": "o",
        "ô": "o",
        "ồ": "o",
        "ố": "o",
        "ộ": "o",
        "ổ": "o",
        "ỗ": "o",
        "ơ": "o",
        "ờ": "o",
        "ớ": "o",
        "ợ": "o",
        "ở": "o",
        "ỡ": "o",
        "ù": "u",
        "ú": "u",
        "ụ": "u",
        "ủ": "u",
        "ũ": "u",
        "ư": "u",
        "ừ": "u",
        "ứ": "u",
        "ự": "u",
        "ử": "u",
        "ữ": "u",
        "ỳ": "y",
        "ý": "y",
        "ỵ": "y",
        "ỷ": "y",
        "ỹ": "y",
        "đ": "d",
    }
    return "".join(replacements.get(char, replacements.get(char.lower(), char)) for char in text.lower())


class MemoryState(TypedDict):
    messages: list[dict[str, str]]
    user_profile: dict[str, Any]
    episodes: list[dict[str, Any]]
    semantic_hits: list[dict[str, Any]]
    recent_conversation: list[dict[str, str]]
    injected_prompt: str
    memory_budget: int
    route: dict[str, bool]
    llm_info: dict[str, Any]


class ShortTermMemory:
    """Sliding-window conversation memory for the current session."""

    def __init__(self, max_messages: int = 8) -> None:
        self.max_messages = max_messages
        self.messages: list[dict[str, str]] = []

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def retrieve(self, budget_chars: int) -> list[dict[str, str]]:
        kept: list[dict[str, str]] = []
        used = 0
        for message in reversed(self.messages):
            cost = len(message["content"])
            if kept and used + cost > budget_chars:
                break
            kept.append(message)
            used += cost
        return list(reversed(kept))

    def clear(self) -> None:
        self.messages.clear()


class LongTermProfileMemory:
    """Persistent key-value profile memory with recency-based conflict handling."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _load_all(self) -> dict[str, dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save_all(self, data: dict[str, dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def retrieve(self, user_id: str) -> dict[str, Any]:
        return self._load_all().get(user_id, {})

    def update_facts(self, user_id: str, facts: dict[str, Any], source: str) -> None:
        if not facts:
            return
        data = self._load_all()
        profile = data.setdefault(user_id, {})
        for key, value in facts.items():
            if value in (None, ""):
                continue
            profile[key] = {
                "value": value,
                "updated_at": now_iso(),
                "source": source,
            }
        self._save_all(data)

    def delete_user(self, user_id: str) -> None:
        data = self._load_all()
        data.pop(user_id, None)
        self._save_all(data)


class EpisodicMemory:
    """Persistent task/outcome log for remembering past experiences."""

    def __init__(self, path: Path, max_episodes: int = 100) -> None:
        self.path = path
        self.max_episodes = max_episodes
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _load_all(self) -> list[dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save_all(self, episodes: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(episodes, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_episode(
        self,
        user_id: str,
        task: str,
        trajectory: str,
        outcome: str,
        reflection: str,
    ) -> None:
        episodes = self._load_all()
        episodes.append(
            {
                "user_id": user_id,
                "task": task,
                "trajectory": trajectory,
                "outcome": outcome,
                "reflection": reflection,
                "created_at": now_iso(),
                "last_used_at": None,
                "use_count": 0,
            }
        )
        self._save_all(episodes[-self.max_episodes :])

    def retrieve(self, user_id: str, query: str, k: int = 3) -> list[dict[str, Any]]:
        episodes = [episode for episode in self._load_all() if episode["user_id"] == user_id]
        ranked = []
        for episode in episodes:
            text = " ".join(
                [
                    episode["task"],
                    episode["trajectory"],
                    episode["outcome"],
                    episode["reflection"],
                ]
            )
            score = overlap_score(query, text)
            if score > 0:
                ranked.append((score, episode))
        ranked.sort(key=lambda item: (item[0], item[1]["created_at"]), reverse=True)
        hits = [episode for _, episode in ranked[:k]]
        if hits:
            all_episodes = self._load_all()
            hit_ids = {id(hit) for hit in hits}
            for episode in all_episodes:
                for hit in hits:
                    if episode["created_at"] == hit["created_at"] and id(hit) in hit_ids:
                        episode["last_used_at"] = now_iso()
                        episode["use_count"] += 1
            self._save_all(all_episodes)
        return hits

    def delete_user(self, user_id: str) -> None:
        self._save_all([episode for episode in self._load_all() if episode["user_id"] != user_id])


class SemanticMemory:
    """Keyword-search semantic memory fallback for domain knowledge retrieval."""

    def __init__(self, docs_path: Path) -> None:
        self.docs_path = docs_path
        self.docs = json.loads(self.docs_path.read_text(encoding="utf-8"))

    def retrieve(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        ranked = []
        for doc in self.docs:
            text = f"{doc['title']} {doc['text']} {' '.join(doc.get('tags', []))}"
            score = overlap_score(query, text)
            if score > 0:
                ranked.append((score, doc))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [{"score": score, **doc} for score, doc in ranked[:k]]


@dataclass
class MemoryRouter:
    """Chooses which memory backends are relevant for the current query."""

    profile_keywords: set[str] = field(
        default_factory=lambda: {
            "tên",
            "name",
            "thích",
            "không thích",
            "dị ứng",
            "allergy",
            "ngôn ngữ",
            "style",
            "phong cách",
        }
    )
    episodic_keywords: set[str] = field(
        default_factory=lambda: {"lần trước", "trước đây", "đã từng", "debug", "episode", "outcome"}
    )
    semantic_keywords: set[str] = field(
        default_factory=lambda: {
            "giải thích",
            "khái niệm",
            "ttl",
            "context",
            "vector",
            "semantic",
            "privacy",
            "langgraph",
            "redis",
            "chroma",
        }
    )

    def route(self, query: str) -> dict[str, bool]:
        lowered = query.lower()
        ascii_lowered = deaccent_vietnamese(query)
        wants_profile = any(keyword in lowered for keyword in self.profile_keywords) or any(
            keyword in ascii_lowered
            for keyword in ["ten", "name", "thich", "khong thich", "di ung", "ngon ngu", "style", "phong cach"]
        )
        wants_episode = any(keyword in lowered for keyword in self.episodic_keywords) or any(
            keyword in ascii_lowered for keyword in ["lan truoc", "truoc day", "da tung", "debug", "episode", "outcome"]
        )
        wants_semantic = any(keyword in lowered for keyword in self.semantic_keywords) or any(
            keyword in ascii_lowered
            for keyword in ["giai thich", "khai niem", "ttl", "context", "vector", "semantic", "privacy", "langgraph", "redis", "chroma"]
        )
        return {
            "short_term": True,
            "profile": wants_profile or not (wants_episode or wants_semantic),
            "episodic": wants_episode,
            "semantic": wants_semantic,
        }


def extract_profile_facts(text: str) -> dict[str, str]:
    lowered = text.lower()
    ascii_lowered = deaccent_vietnamese(text)
    facts: dict[str, str] = {}
    asks_for_memory = any(
        marker in ascii_lowered
        for marker in [
            "?",
            " gi",
            " la gi",
            " ten toi la gi",
            " toi ten la gi",
            " la ai",
            " ten gi",
            " nao",
            " nhac lai",
            " vay",
        ]
    )

    correction_name_match = None
    if "khong phai" in ascii_lowered or "a nham" in ascii_lowered or "nham" in ascii_lowered:
        correction_name_match = re.search(r"(?:toi la|minh la|ten toi la|toi ten la)\s+([a-zA-ZÀ-ỹ\s]+)", ascii_lowered, re.I)
    if correction_name_match and not asks_for_memory:
        facts["name"] = correction_name_match.group(1).strip(" .,!").title()

    name_match = re.search(r"(?:tên tôi là|tôi tên là|mình tên là)\s+([A-Za-zÀ-ỹ\s]+)", text, re.I)
    if not name_match:
        name_match = re.search(r"(?:ten toi la|toi ten la|minh ten la|t.n t.i l.)\s+([A-Za-zÀ-ỹ\s]+)", ascii_lowered, re.I)
    if name_match and not asks_for_memory and "name" not in facts:
        facts["name"] = name_match.group(1).strip(" .,!").title()

    allergy_correction = re.search(
        r"dị ứng\s+(?:với\s+)?(.+?)\s+chứ không phải\s+(.+?)(?:[.!?]|$)",
        text,
        re.I,
    )
    allergy_match = re.search(r"dị ứng\s+(?:với\s+)?(.+?)(?:[.!?]|$)", text, re.I)
    if allergy_correction:
        facts["allergy"] = allergy_correction.group(1).strip(" .,!").lower()
    elif allergy_match:
        facts["allergy"] = allergy_match.group(1).strip(" .,!").lower()
    else:
        ascii_allergy_correction = re.search(
            r"di\s+ung\s+(?:voi\s+)?(.+?)\s+chu khong phai\s+(.+?)(?:[.!?]|$)",
            ascii_lowered,
            re.I,
        )
        ascii_allergy_match = re.search(r"di\s+ung\s+(?:voi\s+)?(.+?)(?:[.!?]|$)", ascii_lowered, re.I)
        if ascii_allergy_correction:
            facts["allergy"] = ascii_allergy_correction.group(1).strip(" .,!").lower()
        elif ascii_allergy_match:
            facts["allergy"] = ascii_allergy_match.group(1).strip(" .,!").lower()

    like_match = re.search(r"tôi thích\s+(.+?)(?:[.!?]|$)", text, re.I)
    if not like_match:
        like_match = re.search(r"toi thich\s+(.+?)(?:[.!?]|$)", ascii_lowered, re.I)
    if like_match and "không thích" not in lowered:
        facts["likes"] = like_match.group(1).strip(" .,!").lower()

    dislike_match = re.search(r"không thích\s+(.+?)(?:[.!?]|$)", text, re.I)
    if not dislike_match:
        dislike_match = re.search(r"khong thich\s+(.+?)(?:[.!?]|$)", ascii_lowered, re.I)
    if dislike_match:
        facts["dislikes"] = dislike_match.group(1).strip(" .,!").lower()

    language_match = re.search(r"(?:ưu tiên|hãy dùng|trả lời bằng)\s+(tiếng [A-Za-zÀ-ỹ]+)", text, re.I)
    if not language_match:
        language_match = re.search(r"(?:uu tien|hay dung|tra loi bang)\s+(tieng [A-Za-zÀ-ỹ]+)", ascii_lowered, re.I)
    if language_match:
        facts["language"] = language_match.group(1).strip(" .,!").lower()

    if "ngắn gọn" in lowered or "ngan gon" in ascii_lowered:
        facts["style"] = "ngắn gọn"
    elif "thật chi tiết" in lowered or "chi tiết" in lowered or "chi tiet" in ascii_lowered:
        facts["style"] = "chi tiết, dễ hiểu"

    skill_match = re.search(r"tôi đang học\s+(.+?)(?:[.!?]|$)", text, re.I)
    if not skill_match:
        skill_match = re.search(r"toi dang hoc\s+(.+?)(?:[.!?]|$)", ascii_lowered, re.I)
    if skill_match:
        facts["learning"] = skill_match.group(1).strip(" .,!").lower()

    return facts


def extract_episode(text: str) -> dict[str, str] | None:
    lowered = text.lower()
    ascii_lowered = deaccent_vietnamese(text)
    has_outcome = (
        "kết quả:" in lowered
        or "outcome:" in lowered
        or "hoàn tất" in lowered
        or "ket qua:" in ascii_lowered
        or "hoan tat" in ascii_lowered
    )
    if not has_outcome:
        return None
    task = "general task"
    task_match = re.search(r"(?:task|nhiệm vụ|hôm nay ta)\s*:?\s*(.+?)(?:\.|;|,|kết quả:|outcome:|$)", text, re.I)
    if not task_match:
        task_match = re.search(r"(?:task|nhiem vu|hom nay ta)\s*:?\s*(.+?)(?:\.|;|,|ket qua:|outcome:|$)", ascii_lowered, re.I)
    if task_match:
        task = task_match.group(1).strip(" .,!").lower()
    outcome = "completed"
    outcome_match = re.search(r"(?:kết quả|outcome)\s*:\s*(.+?)(?:[.!?]|$)", text, re.I)
    if not outcome_match:
        outcome_match = re.search(r"(?:ket qua|outcome)\s*:\s*(.+?)(?:[.!?]|$)", ascii_lowered, re.I)
    if outcome_match:
        outcome = outcome_match.group(1).strip(" .,!").lower()
    reflection = "Prefer the approach that produced the successful outcome."
    reflection_match = re.search(r"(?:bài học|reflection)\s*:\s*(.+?)(?:[.!?]|$)", text, re.I)
    if not reflection_match:
        reflection_match = re.search(r"(?:bai hoc|reflection)\s*:\s*(.+?)(?:[.!?]|$)", ascii_lowered, re.I)
    if reflection_match:
        reflection = reflection_match.group(1).strip(" .,!").lower()
    return {
        "task": task,
        "trajectory": text.strip(),
        "outcome": outcome,
        "reflection": reflection,
    }


def plain_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {key: meta.get("value") for key, meta in profile.items()}


class RealLLMClient:
    """Small wrapper that calls a real hosted LLM while keeping the lab offline-friendly."""

    def __init__(self, provider: str = "auto", model: str | None = None) -> None:
        self._load_env()
        self.provider = provider or os.getenv("LLM_PROVIDER") or "auto"
        self.model = model

    def _load_env(self) -> None:
        try:
            from dotenv import load_dotenv

            load_dotenv(".env")
        except Exception:
            pass

    def generate(self, query: str, memory_prompt: str) -> tuple[str, dict[str, Any]]:
        errors: list[str] = []
        provider = self.provider.lower()

        if provider in {"auto", "openai"} and os.getenv("OPENAI_API_KEY"):
            try:
                return self._generate_openai(query, memory_prompt)
            except Exception as exc:
                errors.append(f"openai: {self._safe_error(exc)}")
                if provider == "openai":
                    raise

        if provider in {"auto", "gemini"} and os.getenv("GEMINI_API_KEY"):
            try:
                return self._generate_gemini(query, memory_prompt)
            except Exception as exc:
                errors.append(f"gemini: {self._safe_error(exc)}")
                if provider == "gemini":
                    raise

        if not errors:
            errors.append("No usable API key found. Set OPENAI_API_KEY or GEMINI_API_KEY in .env.")
        raise RuntimeError(" | ".join(errors))

    def _safe_error(self, exc: Exception) -> str:
        text = str(exc)
        lowered = text.lower()
        if "invalid_api_key" in lowered or "incorrect api key" in lowered:
            return f"{type(exc).__name__}: invalid API key"
        if "resource_exhausted" in lowered or "quota" in lowered or "rate limit" in lowered:
            return f"{type(exc).__name__}: quota or rate limit exceeded"
        text = re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-***", text)
        text = re.sub(r"AIza[A-Za-z0-9_\-]+", "AIza***", text)
        if len(text) > 350:
            text = text[:350] + "..."
        return f"{type(exc).__name__}: {text}"

    def _generate_openai(self, query: str, memory_prompt: str) -> tuple[str, dict[str, Any]]:
        from openai import OpenAI

        model = self.model or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
        client = OpenAI()
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": self._system_instructions(memory_prompt),
                },
                {
                    "role": "user",
                    "content": query,
                },
            ],
        )
        return response.output_text.strip(), {"used": True, "provider": "openai", "model": model, "error": None}

    def _generate_gemini(self, query: str, memory_prompt: str) -> tuple[str, dict[str, Any]]:
        from google import genai

        model = self.model or os.getenv("GEMINI_MODEL") or "gemini-2.0-flash"
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model=model,
            contents=f"{self._system_instructions(memory_prompt)}\n\nUSER QUESTION:\n{query}",
        )
        return response.text.strip(), {"used": True, "provider": "gemini", "model": model, "error": None}

    def _system_instructions(self, memory_prompt: str) -> str:
        return (
            f"{memory_prompt}\n\n"
            "ANSWERING RULES:\n"
            "- Answer in Vietnamese.\n"
            "- Use MEMORY CONTEXT when it is relevant.\n"
            "- If the user provides a new profile fact, acknowledge that it will be remembered.\n"
            "- If memory is missing, say that the current memory does not contain it.\n"
            "- Be concise but explain enough for a beginner."
        )


class MultiMemoryAgent:
    def __init__(
        self,
        user_id: str = "student",
        storage_dir: str | Path = "memory_store",
        docs_path: str | Path = "data/domain_docs.json",
        memory_budget: int = 1800,
        use_llm: bool = False,
        llm_provider: str | None = None,
        llm_model: str | None = None,
    ) -> None:
        storage_path = Path(storage_dir)
        self.user_id = user_id
        self.memory_budget = memory_budget
        self.use_llm = use_llm
        self.llm_client = RealLLMClient(provider=llm_provider, model=llm_model) if use_llm else None
        self.last_llm_info: dict[str, Any] = {
            "used": False,
            "provider": "rule-based",
            "model": None,
            "error": None,
        }
        self.short_term = ShortTermMemory(max_messages=8)
        self.profile = LongTermProfileMemory(storage_path / "profiles.json")
        self.episodic = EpisodicMemory(storage_path / "episodes.json")
        self.semantic = SemanticMemory(Path(docs_path))
        self.router = MemoryRouter()

    def retrieve_memory(self, state: MemoryState) -> MemoryState:
        query = state["messages"][-1]["content"]
        route = self.router.route(query)
        state["route"] = route
        state["recent_conversation"] = (
            self.short_term.retrieve(self.memory_budget // 2) if route["short_term"] else []
        )
        state["user_profile"] = self.profile.retrieve(self.user_id) if route["profile"] else {}
        state["episodes"] = self.episodic.retrieve(self.user_id, query) if route["episodic"] else []
        state["semantic_hits"] = self.semantic.retrieve(query) if route["semantic"] else []
        state["injected_prompt"] = self.build_memory_prompt(state)
        return state

    def build_memory_prompt(self, state: MemoryState) -> str:
        sections = [
            "SYSTEM: You are a helpful learning assistant.",
            "MEMORY CONTEXT:",
            f"Long-term profile: {plain_profile(state['user_profile']) or 'none'}",
            f"Episodic memories: {self._format_episodes(state['episodes']) or 'none'}",
            f"Semantic knowledge: {self._format_semantic(state['semantic_hits']) or 'none'}",
            f"Recent conversation: {self._format_messages(state['recent_conversation']) or 'none'}",
        ]
        return self._trim_prompt("\n".join(sections), state["memory_budget"])

    def _trim_prompt(self, prompt: str, budget_chars: int) -> str:
        if len(prompt) <= budget_chars:
            return prompt
        header = "SYSTEM: You are a helpful learning assistant.\nMEMORY CONTEXT:\n"
        return header + prompt[-(budget_chars - len(header)) :]

    def _format_messages(self, messages: list[dict[str, str]]) -> str:
        return " | ".join(f"{message['role']}: {message['content']}" for message in messages)

    def _format_episodes(self, episodes: list[dict[str, Any]]) -> str:
        return " | ".join(
            f"task={episode['task']}; outcome={episode['outcome']}; reflection={episode['reflection']}"
            for episode in episodes
        )

    def _format_semantic(self, hits: list[dict[str, Any]]) -> str:
        return " | ".join(f"{hit['title']}: {hit['text']}" for hit in hits)

    def save_memory(self, user_message: str, assistant_message: str) -> None:
        self.short_term.add("user", user_message)
        self.short_term.add("assistant", assistant_message)
        facts = extract_profile_facts(user_message)
        self.profile.update_facts(self.user_id, facts, source=user_message)
        episode = extract_episode(user_message)
        if episode:
            self.episodic.add_episode(self.user_id, **episode)

    def answer(self, user_message: str) -> tuple[str, MemoryState]:
        state: MemoryState = {
            "messages": [{"role": "user", "content": user_message}],
            "user_profile": {},
            "episodes": [],
            "semantic_hits": [],
            "recent_conversation": [],
            "injected_prompt": "",
            "memory_budget": self.memory_budget,
            "route": {},
            "llm_info": self.last_llm_info,
        }
        state = self.retrieve_memory(state)
        response = self._generate_response(user_message, state)
        state["llm_info"] = self.last_llm_info
        self.save_memory(user_message, response)
        return response, state

    def _generate_response(self, query: str, state: MemoryState) -> str:
        if self.use_llm and self.llm_client:
            try:
                response, info = self.llm_client.generate(query, state["injected_prompt"])
                self.last_llm_info = info
                return response
            except Exception as exc:
                self.last_llm_info = {
                    "used": False,
                    "provider": self.llm_client.provider,
                    "model": self.llm_client.model,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                fallback = self._generate_rule_based_response(query, state)
                return f"[LLM unavailable, fallback rule-based] {fallback}"
        self.last_llm_info = {
            "used": False,
            "provider": "rule-based",
            "model": None,
            "error": None,
        }
        return self._generate_rule_based_response(query, state)

    def _generate_rule_based_response(self, query: str, state: MemoryState) -> str:
        lowered = query.lower()
        profile = plain_profile(state["user_profile"])
        learned_facts = extract_profile_facts(query)
        ascii_lowered = deaccent_vietnamese(query)
        asks_for_memory = any(
            marker in ascii_lowered for marker in ["?", " gi", " nao", "nhac lai", "vay", "la ai"]
        )

        if learned_facts and not asks_for_memory:
            keys = ", ".join(sorted(learned_facts))
            return f"Mình đã ghi nhớ các profile fact: {keys}."

        if (
            "tên tôi" in lowered
            or "name của tôi" in lowered
            or "ten toi" in ascii_lowered
            or "toi ten" in ascii_lowered
        ):
            return f"Tên của bạn là {profile['name']}." if profile.get("name") else "Mình chưa có tên của bạn trong memory."

        if ("dị ứng" in lowered or "di ung" in ascii_lowered) and (
            "tôi dị ứng gì" in lowered or "toi di ung gi" in ascii_lowered or "allergy" in lowered
        ):
            return (
                f"Bạn đang dị ứng {profile['allergy']}."
                if profile.get("allergy")
                else "Mình chưa có thông tin dị ứng của bạn."
            )

        if "nên dùng ngôn ngữ" in lowered or "ngôn ngữ nào" in lowered:
            if profile.get("language"):
                return f"Mình sẽ ưu tiên {profile['language']} cho câu trả lời."
            return "Mình chưa biết bạn ưu tiên ngôn ngữ nào."

        if "phong cách" in lowered or "trả lời kiểu nào" in lowered:
            if profile.get("style"):
                return f"Mình sẽ trả lời theo phong cách {profile['style']}."
            return "Mình chưa biết phong cách trả lời bạn muốn."

        if state["episodes"] and any(term in lowered for term in ["lần trước", "trước đây", "debug"]):
            episode = state["episodes"][0]
            return (
                f"Lần trước task '{episode['task']}' có kết quả: {episode['outcome']}. "
                f"Bài học: {episode['reflection']}."
            )

        if state["semantic_hits"]:
            hit = state["semantic_hits"][0]
            return f"Theo semantic memory ({hit['title']}): {hit['text']}"

        if extract_episode(query):
            return "Mình đã lưu episode này để lần sau có thể nhắc lại kinh nghiệm và kết quả."

        return "Mình đã xử lý yêu cầu hiện tại. Nếu có thông tin quan trọng, mình sẽ lưu vào đúng loại memory."

    def delete_user_memory(self) -> None:
        self.short_term.clear()
        self.profile.delete_user(self.user_id)
        self.episodic.delete_user(self.user_id)


class NoMemoryAgent:
    """Baseline agent: no persistent profile, no episodic memory, no semantic retrieval."""

    def __init__(self) -> None:
        self.short_term = ShortTermMemory(max_messages=2)

    def answer(self, user_message: str) -> str:
        lowered = user_message.lower()
        if "tên tôi" in lowered:
            response = "Mình không biết tên của bạn vì baseline không có long-term memory."
        elif "dị ứng" in lowered and ("tôi dị ứng gì" in lowered or "allergy" in lowered):
            response = "Mình không biết thông tin dị ứng của bạn vì baseline không lưu profile."
        elif any(term in lowered for term in ["lần trước", "trước đây", "debug"]):
            response = "Mình không có episodic memory nên không nhớ task trước đó."
        elif any(term in lowered for term in ["ttl", "context", "semantic", "privacy", "langgraph"]):
            response = "Mình chỉ có prompt hiện tại nên câu trả lời thiếu nguồn semantic memory."
        else:
            response = "Baseline đã trả lời theo prompt hiện tại nhưng không lưu memory."
        self.short_term.add("user", user_message)
        self.short_term.add("assistant", response)
        return response
