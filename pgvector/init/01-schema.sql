-- COSCUP 2026 · pgvector 對照組
-- PostgreSQL 18 + pgvector 0.8.x：vector 型別 + 距離運算子 + HNSW ANN 索引

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS faq_chunks (
    id          SERIAL PRIMARY KEY,
    doc_id      VARCHAR(64)  NOT NULL UNIQUE,
    category    VARCHAR(32)  NOT NULL,
    title       VARCHAR(255) NOT NULL,
    content     TEXT         NOT NULL,
    embedding   vector(1024) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_faq_category ON faq_chunks (category);

-- HNSW 索引（cosine）。demo 時會現場展示建立前後的 EXPLAIN 差異，
-- 因此預設「不」在 init 建立，由 make pg-index 或 bench 腳本建立：
--   CREATE INDEX idx_faq_embedding ON faq_chunks
--   USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- 查詢範例：
--   SELECT id, title, embedding <=> $1 AS dist
--   FROM faq_chunks ORDER BY embedding <=> $1 LIMIT 5;
