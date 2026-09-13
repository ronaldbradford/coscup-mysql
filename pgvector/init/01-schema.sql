-- COSCUP 2026 · pgvector control group
-- PostgreSQL 18 + pgvector 0.8.x: vector type + distance operators + HNSW ANN index

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

-- HNSW index (cosine). The talk shows EXPLAIN before vs after the index,
-- so we do *not* create it during init. Use make pg-index or the bench script:
--   CREATE INDEX idx_faq_embedding ON faq_chunks
--   USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Query example:
--   SELECT id, title, embedding <=> $1 AS dist
--   FROM faq_chunks ORDER BY embedding <=> $1 LIMIT 5;
