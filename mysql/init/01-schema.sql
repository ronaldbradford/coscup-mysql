-- COSCUP 2026 · MySQL-based RAG demo
-- MySQL 9.x (Community): VECTOR type exists, but DISTANCE() and ANN indexes do not
-- Distance is computed in the app (app/search_mysql.py) with NumPy

CREATE DATABASE IF NOT EXISTS ragdemo CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE ragdemo;

CREATE TABLE IF NOT EXISTS faq_chunks (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    doc_id      VARCHAR(64)  NOT NULL,               -- dataset id
    category    VARCHAR(32)  NOT NULL,               -- metadata: key for pre-retrieval coarse filter
    title       VARCHAR(255) NOT NULL,
    content     TEXT         NOT NULL,
    -- MySQL 9.0+ VECTOR(N): 4 bytes/dim float32 binary storage
    -- Write with STRING_TO_VECTOR('[...]'); read raw binary into np.frombuffer
    embedding   VECTOR(1024) NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_doc (doc_id),
    KEY idx_category (id, category)                  -- used to demo metadata filtering
) ENGINE=InnoDB;

-- Demo: VECTOR helpers available in Community
--   SELECT VECTOR_DIM(embedding) FROM faq_chunks LIMIT 1;
--   SELECT VECTOR_TO_STRING(embedding) FROM faq_chunks LIMIT 1;
-- Not available in Community (HeatWave / MySQL AI only):
--   SELECT DISTANCE(embedding, STRING_TO_VECTOR('[...]'), 'COSINE') ...  -- ERROR 1305
