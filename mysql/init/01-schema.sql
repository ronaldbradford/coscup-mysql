-- COSCUP 2026 · MySQL-based RAG demo
-- MySQL 9.x（社群版）：有 VECTOR 型別，但沒有 DISTANCE() 與 ANN 索引
-- 距離計算改由應用端（app/search_mysql.py）以 NumPy 完成

CREATE DATABASE IF NOT EXISTS ragdemo CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE ragdemo;

CREATE TABLE IF NOT EXISTS faq_chunks (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    doc_id      VARCHAR(64)  NOT NULL,               -- 對應 dataset 的 id
    category    VARCHAR(32)  NOT NULL,               -- metadata：檢索前粗過濾的關鍵
    title       VARCHAR(255) NOT NULL,
    content     TEXT         NOT NULL,
    -- MySQL 9.0+ 的 VECTOR(N)：每維 4 bytes（float32）的 binary 儲存
    -- 寫入用 STRING_TO_VECTOR('[...]')，讀出可取原始 binary 直接 np.frombuffer
    embedding   VECTOR(1024) NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_doc (doc_id),
    KEY idx_category (id, category)                  -- 展示 metadata 過濾用
) ENGINE=InnoDB;

-- 展示用：VECTOR 相關函式（社群版可用的就這些）
--   SELECT VECTOR_DIM(embedding) FROM faq_chunks LIMIT 1;
--   SELECT VECTOR_TO_STRING(embedding) FROM faq_chunks LIMIT 1;
-- 社群版沒有的（HeatWave / MySQL AI 專屬）：
--   SELECT DISTANCE(embedding, STRING_TO_VECTOR('[...]'), 'COSINE') ...  -- ERROR 1305
