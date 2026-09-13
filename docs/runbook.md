# On-site runbook (talk-day operations)

## D-1 (the day before)

- [ ] Boot the VM; `docker compose ps` shows three services healthy
- [ ] `make ingest` to restore the clean 43-row knowledge base (if you ran bench earlier)
- [ ] Acceptance trio: `search_mysql.py` / `search_pg.py` / `chatbot.py -q`
- [ ] Save before/after HNSW `EXPLAIN ANALYZE` screenshots in the slides backup folder
- [ ] Benchmark numbers are in the slide table (use *your* VM numbers)
- [ ] Pre-recorded clips (three, see below) saved on the laptop *and* the phone
- [ ] Laptop fallback env: `make up` once to confirm it starts
- [ ] tmux session `demo` ready, font 20pt, terminal colors readable on the projector

### Pre-record list (OBS or asciinema)

1. `demo1.mp4` (3 min): search_mysql + chatbot, both questions end to end
2. `demo2.mp4` (2 min): pgvector query + EXPLAIN before/after the index
3. `demo3.mp4` (1 min, optional): MyVector ANN query

## Talk day T-60 minutes

- [ ] Boot the VM (if you shut it down overnight); `tmux attach -t demo`
- [ ] Phone hotspot as backup; connect the laptop to it once to confirm it works
- [ ] Warm up with `ollama run qwen3:4b "hi"` (load the model into memory so the first live question is not a 20-second stall)
- [ ] Full dry run: `chatbot.py -q "test"`
- [ ] Projector check: terminal ↔ slides switch is smooth (slides on one virtual desktop, terminal on the other)

## Live command sequence (type these)

### Demo I (12:00–20:00)

```bash
# 1. Show the schema (mysql-cli pane)
DESC faq_chunks;
SELECT VECTOR_DIM(embedding), LENGTH(embedding) FROM faq_chunks LIMIT 1;

# 2. Live gag: Community has no DISTANCE (expect the “oh” from the room)
SELECT DISTANCE(embedding, STRING_TO_VECTOR('[1,2]'), 'COSINE') FROM faq_chunks LIMIT 1;
-- ERROR 1305 (42000): FUNCTION ragdemo.DISTANCE does not exist

# 3. Semantic retrieval (app pane)
python3 search_mysql.py "How long until my refund arrives?"
python3 search_mysql.py "When will the money go back to my card"   # different wording, same answer → why semantic search exists

# 4. Full AI-support Q&A
python3 chatbot.py
# Q1: I bought a shirt last week and want a larger size. Is there a fee?
# Q2: I got a call telling me to go to an ATM to cancel an installment. Is that real?
```

### Demo II (25:00–30:00)

```bash
python3 chatbot.py --db pg -q "What happens if I don't pick up a convenience-store order?"   # same app, one flag

# psql pane: distance computed in the DB
SELECT doc_id, title, embedding <=> (SELECT embedding FROM faq_chunks WHERE doc_id='ship-003') AS dist
FROM faq_chunks ORDER BY dist LIMIT 3;

# EXPLAIN: no index → seq scan
EXPLAIN ANALYZE SELECT id FROM faq_chunks ORDER BY embedding <=> '[0.1, ...]' LIMIT 5;
# Build HNSW (instant on 43 rows; talk 100k from slide screenshots)
CREATE INDEX idx_faq_embedding ON faq_chunks USING hnsw (embedding vector_cosine_ops);
EXPLAIN ANALYZE ...  -- Index Scan using idx_faq_embedding
```

> psql EXPLAIN needs a real vector literal, too long to type live. Before the talk, save both
> EXPLAIN statements in `~/demo_snippets.sql` and run `\i demo_snippets.sql` on stage.

## Incident table

| Situation | Response | Stage line |
| --- | --- | --- |
| Venue Wi-Fi dies | Switch to phone hotspot and SSH again (tmux keeps state) | “While we reconnect, look at the architecture slide” |
| SSH is completely down | Switch to the laptop compose env | Seamless; same commands |
| Ollama LLM stuck / too slow | `chatbot.py --no-llm` for retrieval only; play demo1.mp4 for the LLM part | “LLM generation is not today’s point; the retrieval layer is” |
| MySQL container dies | `docker compose restart mysql` (~20 s) | Do the pgvector section first, come back |
| Projector signal issues | Fall back to pre-recorded video + narration | Copies on laptop and phone |
| Badly behind schedule | Follow the talk-design cut table: drop MyVector live first, then chatbot Q2 | Never cut the decision framework |

## Close (hold this slide through Q&A)

Hold the last slide: repo QR code + thumbnail of the three-way decision diagram + contact (litotom).
Dead-air backup: ask yourself “will someone ask about MariaDB?” (answer is expected question 5 in talk-design).
