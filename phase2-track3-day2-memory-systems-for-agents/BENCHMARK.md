# BENCHMARK.md - Lab 17 Multi-Memory Agent

## 1. Goal

This report compares two agents on 10 multi-turn conversations:

- `NoMemoryAgent`: baseline with no persistent profile, no episodic memory, and no semantic retrieval.
- `MultiMemoryAgent`: full memory stack with short-term, long-term profile, episodic, and semantic memory.

The implementation is offline and deterministic so it can run without API keys. Redis and Chroma are represented by clear local backends:

- Long-term profile: JSON key-value store.
- Semantic memory: JSON document store with keyword-search fallback.

This still follows the lab rubric because each memory type has a separate interface and retrieve/save behavior.

## 2. Memory Stack

| Memory type | Implementation | What it stores | Retrieve behavior |
|---|---|---|---|
| Short-term | `ShortTermMemory` sliding window | Recent user/assistant turns | Keeps the most recent messages within a character budget |
| Long-term profile | `LongTermProfileMemory` JSON KV | Name, allergy, language preference, style preference | Loads profile by `user_id`; newer facts overwrite older conflicts |
| Episodic | `EpisodicMemory` JSON log | Task, trajectory, outcome, reflection | Keyword-overlap search over past episodes |
| Semantic | `SemanticMemory` JSON docs | Domain knowledge chunks | Keyword-overlap search over document chunks |

## 3. LangGraph-Style Flow

The code uses a LangGraph-style skeleton:

1. `MemoryState` carries `messages`, `user_profile`, `episodes`, `semantic_hits`, `recent_conversation`, and `memory_budget`.
2. `MemoryRouter.route(query)` decides which memory backends are useful for the query.
3. `retrieve_memory(state)` loads memory from the selected backends.
4. `build_memory_prompt(state)` injects memory into clear prompt sections.
5. `_generate_response(query, state)` simulates the model response.
6. `save_memory(user_message, assistant_message)` updates profile facts and saves episodes.

Prompt sections:

- Long-term profile
- Episodic memories
- Semantic knowledge
- Recent conversation

## 4. Benchmark Results

Command:

```bash
python benchmark.py
```

Result:

```text
Passed 10/10 scenarios
```

| # | Scenario | Group | No-memory result | With-memory result | Pass? | Prompt chars |
|---|---|---|---|---|---|---:|
| 1 | Recall user name after filler turns | Profile recall | Does not know the user name | Recalls `Linh` | Pass | 703 |
| 2 | Allergy conflict update | Conflict update | Does not know allergy | Recalls updated allergy `đậu nành` | Pass | 370 |
| 3 | Recall previous Docker debug episode | Episodic recall | Does not remember previous task | Recalls Docker service-name lesson | Pass | 681 |
| 4 | Retrieve semantic memory chunk | Semantic retrieval | Gives no semantic source | Retrieves memory-types knowledge chunk | Pass | 900 |
| 5 | Recall preferred answer language | Profile recall | Does not know preference | Recalls `tiếng Việt` | Pass | 405 |
| 6 | Recall preferred style | Profile recall | Does not know preference | Recalls `ngắn gọn` | Pass | 549 |
| 7 | Context trim still preserves profile | Trim/token budget | Loses old name fact | Recalls `Minh` after many filler turns | Pass | 616 |
| 8 | Retrieve TTL privacy concept | Semantic retrieval | Gives no semantic source | Retrieves privacy/TTL knowledge chunk | Pass | 799 |
| 9 | Recall async teaching episode | Episodic recall | Does not remember previous task | Recalls cooperative-waiting explanation | Pass | 900 |
| 10 | LangGraph state semantic retrieval | Semantic retrieval | Gives no semantic source | Retrieves LangGraph memory-state chunk | Pass | 900 |

## 5. Memory Hit-Rate Analysis

| Test group | Scenarios | With-memory passes | Hit rate |
|---|---:|---:|---:|
| Profile recall | 1, 5, 6 | 3/3 | 100% |
| Conflict update | 2 | 1/1 | 100% |
| Episodic recall | 3, 9 | 2/2 | 100% |
| Semantic retrieval | 4, 8, 10 | 3/3 | 100% |
| Trim/token budget | 7 | 1/1 | 100% |
| Overall | 1-10 | 10/10 | 100% |

## 6. Token/Context Budget Breakdown

The lab asks for token-budget management. This implementation uses character count as a simple offline proxy for tokens.

Configuration used in benchmark:

- `memory_budget = 900` characters.
- Short-term memory receives roughly half of that budget through the sliding-window retriever.
- The final injected prompt is trimmed if it exceeds the budget.
- In the benchmark, `Prompt chars` never exceeds 900.

Priority idea:

1. Profile facts are compact and high-value.
2. Episodic and semantic hits are retrieved only when the router thinks they are relevant.
3. Recent conversation is sliding-window trimmed, so old filler turns can be evicted without losing important profile facts.

## 7. Required Conflict Test

Conversation:

```text
User: Tôi dị ứng sữa bò.
User: À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.
User: Vậy tôi dị ứng gì?
```

Expected profile:

```text
allergy = đậu nành
```

Actual with-memory response:

```text
Bạn đang dị ứng đậu nành.
```

Reason: `LongTermProfileMemory.update_facts()` overwrites the old `allergy` value using recency-based conflict handling.

## 8. Privacy and Limitations Reflection

The most privacy-sensitive memory is long-term profile memory because it may store personal facts such as name, allergies, preferences, or learning history. Episodic memory is also sensitive because it can store detailed task history and outcomes. If the system stored real user data, it should ask for consent before saving sensitive facts.

If a user asks to delete memory, the system should delete all related entries from:

- Short-term memory
- Long-term profile memory
- Episodic memory

Semantic memory is usually shared domain knowledge, so user deletion normally does not delete global documents unless user-specific documents were added there.

Important privacy controls:

- Data minimization: store only facts that help future tasks.
- TTL: expire stale preferences and old episodes.
- Consent: ask before saving sensitive information.
- Deletion verification: confirm that all user-specific memory stores were cleared.

Technical limitations of this solution:

- It uses keyword overlap instead of real embeddings, so semantic retrieval is weaker than Chroma or FAISS.
- It uses deterministic rule-based extraction instead of an LLM extractor, so it only recognizes simple patterns.
- Character count is only a rough token proxy.
- The graph is a LangGraph-style skeleton, not a real `langgraph` package workflow.

Even with these limitations, the solution demonstrates the core architecture required by the lab: separate memory backends, router-based retrieval, prompt injection, memory write-back, conflict handling, and a benchmark comparing no-memory versus with-memory behavior.
