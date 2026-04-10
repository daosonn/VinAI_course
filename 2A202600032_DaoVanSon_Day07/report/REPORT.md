# Bao Cao Lab 7: Embedding & Vector Store

**Ho ten:** Đào Văn Sơn
**Ngay:** 2026-04-10

---

## 1. Warm-up (5 diem)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghia la gi?**
> High cosine similarity (gan 1.0) cho biet hai vector co huong gan giong nhau trong khong gian embedding, tuc la hai doan van ban co noi dung ngu nghia tuong dong.

**Vi du HIGH similarity:**
- Sentence A: "Python is a programming language"
- Sentence B: "Python is used for software development"
- Tai sao tuong dong: Ca hai cau deu noi ve Python va lap trinh/phat trien phan mem, chia se ngua canh ngu nghia giong nhau.

**Vi du LOW similarity:**
- Sentence A: "I love cooking pasta"
- Sentence B: "Quantum physics is fascinating"
- Tai sao khac: Hai cau thuoc hai linh vuc hoan toan khac nhau (nau an vs vat ly luong tu), khong co tu vung hay ngu nghia chung.

**Tai sao cosine similarity duoc uu tien hon Euclidean distance cho text embeddings?**
> Cosine similarity do goc giua hai vector, khong phu thuoc vao do dai (magnitude) cua chung. Dieu nay quan trong vi cac van ban co do dai khac nhau van co the co ngu nghia giong nhau - cosine chi quan tam den huong cua vector, khong quan tam den kich thuoc.

### Chunking Math (Ex 1.2)

**Document 10,000 ky tu, chunk_size=500, overlap=50. Bao nhieu chunks?**
> Phep tinh: step = chunk_size - overlap = 500 - 50 = 450
> So chunks = ceil((10000 - 500) / 450) + 1 = ceil(9500 / 450) + 1 = ceil(21.11) + 1 = 22 + 1 = 23
> **Dap an: 23 chunks** (chunk cuoi cung chua phan con lai)

**Neu overlap tang len 100, chunk count thay doi the nao? Tai sao muon overlap nhieu hon?**
> step = 500 - 100 = 400, so chunks = ceil(9500/400) + 1 = ceil(23.75) + 1 = 25. Tang overlap tu 50 len 100 lam tang so chunks tu 23 len 25. Overlap lon hon giup dam bao ngu canh khong bi mat tai diem cat - cac cau o ranh gioi chunk se xuat hien trong ca hai chunk ke nhau, giup retrieval chinh xac hon.

---

## 2. Document Selection -- Nhom (10 diem)

### Domain & Ly Do Chon

**Domain:** AI/ML Knowledge Base (tai lieu ve Python, RAG, Vector Store, Chunking)

**Tai sao nhom chon domain nay?**
> Nhom chon domain AI/ML knowledge base vi day la linh vuc lien quan truc tiep den noi dung bai lab. Cac tai lieu co san trong thu muc data/ bao gom nhieu khia canh cua he thong RAG, giup viec kiem tra retrieval co y nghia thuc te. Domain nay cung co su da dang ve ngon ngu (tieng Anh va tieng Viet) de kiem tra kha nang xu ly da ngon ngu.

### Data Inventory

| # | Ten tai lieu | Nguon | So ky tu | Metadata da gan |
|---|--------------|-------|----------|-----------------|
| 1 | python_intro.txt | Lab data | 1,944 | source, lang=en |
| 2 | vector_store_notes.md | Lab data | ~1,500 | source, lang=en |
| 3 | rag_system_design.md | Lab data | 2,391 | source, lang=en |
| 4 | customer_support_playbook.txt | Lab data | ~1,200 | source, lang=en |
| 5 | chunking_experiment_report.md | Lab data | ~1,800 | source, lang=en |
| 6 | vi_retrieval_notes.md | Lab data | ~1,600 | source, lang=vi |

### Metadata Schema

| Truong metadata | Kieu | Vi du gia tri | Tai sao huu ich cho retrieval? |
|----------------|------|---------------|-------------------------------|
| source | string | "python_intro.txt" | Giup truy vet nguon goc cua chunk, loc ket qua theo tai lieu cu the |
| lang | string | "en", "vi" | Cho phep loc ket qua theo ngon ngu, tranh tra ve chunk tieng Viet khi query tieng Anh |
| doc_id | string | "python_intro.txt_0" | Dinh danh duy nhat de quan ly va xoa document |

---

## 3. Chunking Strategy -- Ca nhan chon, nhom so sanh (15 diem)

### Baseline Analysis

Chay `ChunkingStrategyComparator().compare()` tren 2 tai lieu:

| Tai lieu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| python_intro.txt | FixedSizeChunker (`fixed_size`) | 10 | 194.4 | Khong - cat giua cau |
| python_intro.txt | SentenceChunker (`by_sentences`) | 5 | 387.0 | Tot - giu nguyen cau |
| python_intro.txt | RecursiveChunker (`recursive`) | 14 | 136.9 | Tot - uu tien ranh gioi tu nhien |
| rag_system_design.md | FixedSizeChunker (`fixed_size`) | 12 | 199.2 | Khong - cat giua cau |
| rag_system_design.md | SentenceChunker (`by_sentences`) | 5 | 476.0 | Tot nhung chunk lon |
| rag_system_design.md | RecursiveChunker (`recursive`) | 20 | 117.7 | Tot - tach theo paragraph |

### Strategy Cua Toi

**Loai:** RecursiveChunker

**Mo ta cach hoat dong:**
> RecursiveChunker su dung danh sach separator theo thu tu uu tien: "\n\n" (paragraph), "\n" (dong), ". " (cau), " " (tu), "" (ky tu). Truoc tien, no co chia text theo separator uu tien cao nhat. Neu chunk van con qua lon, no tiep tuc chia bang separator tiep theo. Cac chunk nho duoc gop lai voi nhau de khong qua be.

**Tai sao toi chon strategy nay cho domain nhom?**
> Tai lieu AI/ML thuong co cau truc ro rang voi cac heading, paragraph, va bullet points. RecursiveChunker khai thac cau truc nay bang cach uu tien tach tai paragraph boundaries truoc, giu nguyen ngu canh cua tung phan. Dieu nay tot hon FixedSizeChunker (cat bat ke ranh gioi) va SentenceChunker (khong xet den cau truc van ban).

**Code snippet (neu custom):**
```python
# Su dung RecursiveChunker voi cau hinh mac dinh
chunker = RecursiveChunker(chunk_size=300)
chunks = chunker.chunk(document_text)
```

### So Sanh: Strategy cua toi vs Baseline

| Tai lieu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|-------------|------------|--------------------|
| python_intro.txt | best baseline (SentenceChunker) | 5 | 387.0 | Chunk lon, chua nhieu thong tin nhung co the thua |
| python_intro.txt | **RecursiveChunker** | 14 | 136.9 | Chunk nho, tap trung, de retrieve chinh xac |

### So Sanh Voi Thanh Vien Khac

| Thanh vien | Strategy | Retrieval Score (/10) | Diem manh | Diem yeu |
|-----------|----------|----------------------|-----------|----------|
| Toi | RecursiveChunker | 7/10 | Giu nguyen cau truc, kich thuoc deu | Chunk co the hoi nho |
| Tài | SentenceChunker | 6/10 | Cau hoan chinh | Chunk khong deu |
| Quang | FixedSizeChunker | 5/10 | Don gian, deu | Mat ngu canh |

**Strategy nao tot nhat cho domain nay? Tai sao?**
> RecursiveChunker la lua chon tot nhat cho domain AI/ML documentation vi no ton trong cau truc tu nhien cua van ban (heading, paragraph). Dieu nay giup moi chunk chua noi dung ve mot chu de cu the, lam tang do chinh xac khi retrieve.

---

## 4. My Approach -- Ca nhan (10 diem)

Giai thich cach tiep can khi implement cac phan chinh trong package `src`.

### Chunking Functions

**`SentenceChunker.chunk`** -- approach:
> Su dung regex `re.split(r'(?<=[.!?])\s', text)` de tach cau tai cac ranh gioi cau (sau dau ., !, ? theo sau boi khoang trang). Sau do nhom cac cau lai theo `max_sentences_per_chunk` bang cach duyet tuan tu va noi bang dau cach. Xu ly edge case: text rong tra ve [], text khong co dau cau tra ve nguyen van.

**`RecursiveChunker.chunk` / `_split`** -- approach:
> Algorithm de quy: base case la khi text ngan hon chunk_size thi tra ve nguyen van. Neu khong, thu tach bang separator dau tien trong danh sach. Neu tach duoc, gop cac phan nho lai voi nhau (de khong qua be) va de quy tren cac phan con qua lon voi separator tiep theo. Neu separator khong ton tai trong text, chuyen sang separator tiep theo. Fallback cuoi cung la cat theo ky tu.

### EmbeddingStore

**`add_documents` + `search`** -- approach:
> Moi document duoc chuyen thanh record gom: content, embedding vector (tu embedding_fn), metadata (bao gom doc_id). Luu vao list `_store`. Khi search, embed query, tinh dot product voi tung record (vi mock embeddings da normalize), sap xep giam dan theo score, tra ve top_k.

**`search_with_filter` + `delete_document`** -- approach:
> `search_with_filter` loc truoc: duyet qua `_store`, chi giu nhung record ma metadata khop voi tat ca key-value trong filter. Sau do chay search binh thuong tren tap da loc. `delete_document` dung list comprehension de loai bo tat ca record co `metadata['doc_id']` khop, tra ve True/False dua tren kich thuoc truoc va sau.

### KnowledgeBaseAgent

**`answer`** -- approach:
> Goi `store.search(question, top_k)` de lay cac chunk lien quan nhat. Noi noi dung cac chunk thanh context string. Xay dung prompt theo format: "Based on the following context, answer the question.\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:". Goi `llm_fn(prompt)` va tra ve ket qua.

### Test Results

```
tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED

42 passed
```

**So tests pass:** 42 / 42

---

## 5. Similarity Predictions -- Ca nhan (5 diem)

| Pair | Sentence A | Sentence B | Du doan | Actual Score | Dung? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Python is a programming language | Python is used for software development | high | 0.1250 | Khong (mock embeddings khong hieu ngu nghia) |
| 2 | The cat sat on the mat | A dog played in the park | low | -0.0200 | Dung |
| 3 | Machine learning uses data | Deep learning is a subset of ML | high | 0.0256 | Khong (mock khong phan biet) |
| 4 | I love cooking pasta | Quantum physics is fascinating | low | -0.1380 | Dung |
| 5 | Vector databases store embeddings | Embedding stores enable similarity search | high | 0.0763 | Khong (mock khong hieu ngu nghia) |

**Ket qua nao bat ngo nhat? Dieu nay noi gi ve cach embeddings bieu dien nghia?**
> Ket qua bat ngo nhat la Pair 1 va 3 co score rat thap du ngu nghia tuong dong. Dieu nay cho thay mock embeddings (dua tren MD5 hash) khong hieu ngu nghia that su - chung chi tao vector xac dinh tu chuoi ky tu. Voi real embeddings (nhu all-MiniLM-L6-v2 hoac OpenAI), cac cap cau tuong dong se co score cao hon nhieu vi model duoc train de hieu ngu nghia.

---

## 6. Results -- Ca nhan (10 diem)

Chay 5 benchmark queries tren implementation voi mock embeddings.

### Benchmark Queries & Gold Answers (nhom thong nhat)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | What are the benefits of using Python for AI? | Python co he sinh thai phong phu (PyTorch, TensorFlow, scikit-learn) va cu phap don gian, phu hop cho AI/ML |
| 2 | How does a vector store work? | Vector store luu tru embeddings va thuc hien similarity search bang cach so sanh vector cua query voi cac vector da luu |
| 3 | What chunking strategy is best? | Khong co strategy tot nhat tuyet doi - recursive chunking la lua chon tot cho hau het truong hop vi can bang giua kich thuoc va ngu canh |
| 4 | How to evaluate a RAG system? | Danh gia RAG can kiem tra retrieval precision, chunk coherence, grounding quality va su dung realistic queries |
| 5 | What is the role of metadata in retrieval? | Metadata cho phep loc ket qua truoc khi search, giup thu hep pham vi va tang do chinh xac |

### Ket Qua Cua Toi

| # | Query | Top-1 Retrieved Chunk (tom tat) | Score | Relevant? | Agent Answer (tom tat) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | What are the benefits of Python for AI? | rag_system_design.md - Operational considerations | 0.2412 | Khong chinh xac (mock) | Answer based on context |
| 2 | How does a vector store work? | chunking_experiment_report.md - Recursive chunking | 0.2501 | Khong chinh xac (mock) | Answer based on context |
| 3 | What chunking strategy is best? | vi_retrieval_notes.md | 0.2557 | Mot phan | Answer based on context |
| 4 | How to evaluate a RAG system? | (mock embeddings - random match) | ~0.23 | Khong chinh xac (mock) | Answer based on context |
| 5 | What is the role of metadata? | (mock embeddings - random match) | ~0.22 | Khong chinh xac (mock) | Answer based on context |

**Bao nhieu queries tra ve chunk relevant trong top-3?** 1 / 5

> **Ghi chu:** Ket qua thap vi su dung mock embeddings (MD5 hash-based), khong hieu ngu nghia that su. Voi real embeddings (sentence-transformers hoac OpenAI), retrieval quality se cao hon dang ke.

---

## 7. What I Learned (5 diem -- Demo)

**Dieu hay nhat toi hoc duoc tu thanh vien khac trong nhom:**
> Hoc duoc rang viec chon chunk_size phu thuoc nhieu vao domain - tai lieu ky thuat can chunk nho hon (200-300 chars) de giu noi dung tap trung, trong khi tai lieu narrative co the dung chunk lon hon (500+ chars) de giu ngu canh cau chuyen.

**Dieu hay nhat toi hoc duoc tu nhom khac (qua demo):**
> Metadata design rat quan trong - nhom khac su dung metadata de loc theo ngon ngu va department, giup tang retrieval precision dang ke ma khong can thay doi embedding model.

**Neu lam lai, toi se thay doi gi trong data strategy?**
> Toi se su dung real embeddings (all-MiniLM-L6-v2) thay vi mock de co ket qua retrieval co y nghia hon. Dong thoi, toi se thiet ke metadata schema ky luong hon tu dau, bao gom cac truong nhu topic, difficulty_level, va document_type de ho tro filtering tot hon.

---

## Tu Danh Gia

| Tieu chi | Loai | Diem tu danh gia |
|----------|------|-------------------|
| Warm-up | Ca nhan | 5 / 5 |
| Document selection | Nhom | 8 / 10 |
| Chunking strategy | Nhom | 12 / 15 |
| My approach | Ca nhan | 9 / 10 |
| Similarity predictions | Ca nhan | 4 / 5 |
| Results | Ca nhan | 7 / 10 |
| Core implementation (tests) | Ca nhan | 30 / 30 |
| Demo | Nhom | 4 / 5 |
| **Tong** | | **79 / 100** |
