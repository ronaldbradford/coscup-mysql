# COSCUP 2026 session design (40-minute version)

**Building a MySQL-based RAG System from Scratch: VECTOR Type in Practice, Engineering Trade-offs, and a pgvector Comparison**

> Speaker: Hank (litotom) · MySQL track · 40 minutes (including ~3 minutes Q&A)

---

## Core narrative (one sentence)

Use the LitoShop e-commerce AI-support case to answer one question honestly: **“We only have MySQL. Can we do RAG without standing up another database?”** — yes, but you have to know what you are doing. Close with a pgvector comparison and a three-way decision framework.

### Why AI support as the case (design rationale)

1. **Everyone gets it**: no business background needed; the audience is oriented in 10 seconds. Q&A is a natural live demo.
2. **It is RAG by nature**: a support knowledge base (FAQ, return policy, shipping rules) is typical retrieval corpus. “Customers ask the same thing a hundred ways” is why vector search exists — you can demo keyword vs semantic search live.
3. **Fully controlled data**: the knowledge base is synthetic LitoShop data built for this demo (43 knowledge chunks, 173 paraphrase queries, scalable to 100,000 rows), CC0, no PII, no copyright issues — it passes COSCUP open-license review.
4. **Scale story is easy to tell**: a real support KB of a few hundred to a few thousand rows is fine as a MySQL full scan (the sweet spot of Demo I). Add product copy and ticket history and you hit hundreds of thousands of vectors — the narrative jump into the deep end (the benchmark).

### Three-act structure

| Act | Message | Feeling |
| --- | --- | --- |
| Act 1: it works | MySQL 9.x stores VECTOR, the app computes distance, AI support is running | “Oh — it actually works” |
| Act 2: the cost | No DISTANCE(), no ANN; 2 s at 100k vs ~10 ms on pgvector | “That big a gap?” |
| Act 3: the choice | Metadata filter, MyVector plugin, or move to pgvector — a decision framework | “I know how to choose” |

---

## 40-minute beat sheet

### 00:00–03:00 · Open: LitoShop wants AI support (3 min)

- Intro in 30 seconds (Green Bean Soup / litotom blog, 30 years in software, one slide).
- Hook: fictional setup — LitoShop support is asked “how long until my refund arrives?” a hundred times a day, every time in different words. Leadership wants AI support. The architect says add a vector database. The DBA says “don’t we already have MySQL?” → this talk is the full technical answer after that meeting.
- Scope: no LLM training, no vector math, no HeatWave-only features.

### 03:00–07:00 · RAG 101 and “why MySQL” (4 min)

- RAG on one slide: question → embedding → Top-K similarity search → stuff the prompt → LLM answer. Stress that this talk is only about the retrieval-layer database.
- Current shopping list: people jump to Pinecone / Qdrant / Milvus / pgvector and never mention MySQL — yet MySQL is the most common OLTP database already in the enterprise stack. “Don’t move the data, don’t add ops surface, JOIN the transactional tables sitting next to you” is a real engineering incentive.

### 07:00–12:00 · What MySQL VECTOR actually is (5 min)

- `VECTOR(N)` type: introduced in 9.0, 4 bytes/dim float32 binary, max 16,383 dims.
- Community Edition really only has three of the four functions people expect: `STRING_TO_VECTOR`, `VECTOR_TO_STRING`, `VECTOR_DIM`.
- **Live gag (important)**: run `SELECT DISTANCE(...)` live → `ERROR 1305 FUNCTION DISTANCE does not exist`. Official docs say “HeatWave on OCI only”. Still true in 9.7 (2026-04 GA); vector search is still on the roadmap.
- Setup the punchline: you got the type, not the engine — “a car with seats and a steering wheel; you have to find the engine yourself.” That is the architecture premise of the demo.

### 12:00–20:00 · Live Demo I: AI support on MySQL (8 min)

- Architecture in 30 seconds: question → Ollama bge-m3 embedding → MySQL retrieval → Ollama qwen3 generation → answer (fully open source, fully local).
- Schema (1 min): `faq_chunks(doc_id, category, title, content, embedding VECTOR(1024))`; the `category` index is a later payoff.
- Retrieval strategy (2 min): pull candidate rows as raw binary → `np.frombuffer` → rank by dot product. Stress “embeddings are already normalized, cosine = dot product.”
- Live: `python search_mysql.py "How long until my refund arrives?"` — semantic hit on return-004 even though the wording is completely different (1.5 min).
- Live: `python chatbot.py` with 2 questions (3 min):
  - “I bought a shirt last week and want a larger size. Is there a fee?” → hits return-005, answer includes one free exchange.
  - “I got a call telling me to go to an ATM to cancel an installment.” → hits account-001, answer mentions the 165 anti-fraud hotline — RAG making the LLM say the *right* thing.
- Recap: a few hundred FAQ rows, 43 chunks, MySQL retrieval in 2–3 ms — **at this scale, it is enough**.

### 20:00–25:00 · Deep water: the cost of no ANN (5 min)

- Transition question: “What if the knowledge base grows to 100,000 rows?” (add product copy, historical tickets).
- Benchmark chart (reproducible from this repo’s `bench/`; numbers below are from a 7 GB RAM container — use your VM numbers on stage):

  | Scenario | 10k p50 | 100k p50 |
  | --- | --- | --- |
  | MySQL full scan + app-side | 242 ms | 2,144 ms |
  | MySQL category filter (1/10) | 38 ms | 244 ms |
  | pgvector no index (exact) | 39 ms | 469 ms |
  | pgvector HNSW | 2.2 ms | 9.7 ms |

- Read: the full-scan cost is “move 400 MB out of the database on every query.” The bottleneck is network and deserialization, not NumPy.
- Workarounds (how far the MySQL camp can stretch): metadata coarse filter (support naturally has category / tenant, one `WHERE` drops 90% of candidates), partition by tenant, covering index to limit TOP-K candidates, read replica offload.
- Honest close: these delay the collapse; they are not a substitute for ANN.

### 25:00–30:00 · Live Demo II: pgvector control group (5 min)

- Same data, same chatbot, one flag: `--db pg`.
- Show the SQL difference: `ORDER BY embedding <=> :q LIMIT 5` — distance and sort stay in the DB.
- Live: `EXPLAIN ANALYZE` before and after HNSW (seq scan → Index Scan using hnsw).
- One comparison slide: type / dim limit, distance functions, indexes, filter interaction (0.8 iterative scan), ecosystem (halfvec, quantization).
- Reminder: pgvector is not a free lunch — HNSW build time and memory, ANN recall trade-offs, the ops cost of another database.

### 30:00–33:00 · Third path: MyVector (3 min)

- The community built an engine: MyVector plugin (GPLv2, open source), HNSW ANN inside MySQL, index synced via binlog, supports 8.0 / 8.4 / 9.7.
- One SQL example slide: `MYVECTOR(type=HNSW,dim=1024)` column annotation + `MYVECTOR_IS_ANN(...)` query.
- Positioning: proof that the MySQL ecosystem is not idle, but plugin adoption risk (upgrades, support, community size) is yours to judge. Live only if time allows (backup demo); otherwise slides and a pre-recorded clip.

### 33:00–37:00 · Decision framework and close (4 min)

- Three-way decision diagram:
  - **Stay on MySQL**: < 50k vectors, low QPS, natural filter dimensions, no extra ops surface — app-side retrieval is fully valid.
  - **MySQL + MyVector**: you want to stay on MySQL and you need ANN, and you accept third-party plugin risk.
  - **Move to pgvector / a dedicated vector DB**: scale, latency, and recall are hard requirements, or the team already runs Postgres.
- Three takeaways: an AI-support demo you can `docker compose up`, a MySQL vs pgvector comparison table, a selection framework.
- Repo QR code (Apache-2.0 / CC BY-SA 4.0) plus a community close: “go vote vector search onto the official MySQL roadmap.”

### 37:00–40:00 · Q&A (3 min)

Expected questions and prepared answers:

1. “Why not just store vectors in JSON?” → VECTOR is denser (4 B/dim vs text) and type-checked; retrieval strategy is the same.
2. “Doesn’t HeatWave have DISTANCE?” → Yes, as an OCI cloud service, not Community in your data center. This talk covers only what you can get open-source.
3. “What if we change the embedding model?” → A dim change means rebuild the column and re-embed everything. Both sides hurt the same; store the model version in metadata when you design the schema.
4. “What about retrieval quality?” → bge-m3 is strong multilingual; a production system should add a rerank layer, which is out of scope here.
5. “What about MariaDB?” → MariaDB 11.7 has its own VECTOR type and HNSW index. Worth watching — and another talk.

---

## Time-risk control

| Checkpoint | Should be at | Cut if late |
| --- | --- | --- |
| End of Demo I | 20:00 | Ask only 1 chatbot question (cut 1.5 min) |
| Benchmark finished | 25:00 | Workarounds: metadata filter only (cut 1 min) |
| End of Demo II | 30:00 | EXPLAIN from screenshots, not live (cut 1.5 min) |
| End of MyVector | 33:00 | Collapse the section to 1 slide / 1 minute (cut 2 min) |

Rule: **never cut the decision framework (33:00–37:00)** — that is what the audience takes home. MyVector is the most elastic buffer.
