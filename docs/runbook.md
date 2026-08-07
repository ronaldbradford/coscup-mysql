# 現場 Runbook（演講日操作手冊）

## D-1（前一天）

- [ ] VM 開機，`docker compose ps` 三個服務 healthy
- [ ] `make ingest` 還原 43 筆乾淨知識庫（若之前跑過 bench）
- [ ] 驗收三連發：`search_mysql.py` / `search_pg.py` / `chatbot.py -q`
- [ ] `EXPLAIN ANALYZE` 的 HNSW 前後兩張截圖存進簡報備用資料夾
- [ ] benchmark 數字已填入簡報表格（用自己 VM 的數字）
- [ ] 預錄影片（三段，見下）已存筆電本機 + 手機
- [ ] 筆電本機備援環境 `make up` 過一次確認能起
- [ ] tmux session `demo` 建好、字體 20pt、終端機配色確認投影可讀

### 預錄影片清單（用 OBS 或 asciinema）

1. `demo1.mp4`（3 分）：search_mysql + chatbot 兩題完整流程
2. `demo2.mp4`（2 分）：pgvector 查詢 + EXPLAIN 建索引前後
3. `demo3.mp4`（1 分，選配）：MyVector ANN 查詢

## 演講日 T-60 分鐘

- [ ] VM 開機（若前晚有關機），`tmux attach -t demo`
- [ ] 手機開熱點備援，筆電先連過一次確認可用
- [ ] `ollama run qwen3:4b "hi"` 暖機（把模型載進記憶體，避免現場首問延遲 20 秒）
- [ ] `chatbot.py -q "測試"` 完整跑一次
- [ ] 投影測試：終端機 + 簡報切換順暢（建議簡報放印表機側，terminal 放另一側虛擬桌面）

## 現場操作序（照著打即可）

### Demo I（12:00–20:00）

```bash
# 1. 秀 schema（mysql-cli 窗格）
DESC faq_chunks;
SELECT VECTOR_DIM(embedding), LENGTH(embedding) FROM faq_chunks LIMIT 1;

# 2. 現場梗：社群版沒有 DISTANCE（必收「哦～」聲）
SELECT DISTANCE(embedding, STRING_TO_VECTOR('[1,2]'), 'COSINE') FROM faq_chunks LIMIT 1;
-- ERROR 1305 (42000): FUNCTION ragdemo.DISTANCE does not exist

# 3. 語意檢索（app 窗格）
python3 search_mysql.py "退款多久會到？"
python3 search_mysql.py "錢什麼時候退回我卡裡"   # 完全不同問法、同一答案 → 語意檢索的價值

# 4. AI 客服完整問答
python3 chatbot.py
# 問題 1：我上週買的衣服想換大一號，要收費嗎？
# 問題 2：接到電話叫我去 ATM 解除分期，是真的嗎？
```

### Demo II（25:00–30:00）

```bash
python3 chatbot.py --db pg -q "超商的貨過幾天沒領會怎樣"   # 同 app、一參數切換

# psql 窗格：距離計算在 DB 內
SELECT doc_id, title, embedding <=> (SELECT embedding FROM faq_chunks WHERE doc_id='ship-003') AS dist
FROM faq_chunks ORDER BY dist LIMIT 3;

# EXPLAIN：無索引 → seq scan
EXPLAIN ANALYZE SELECT id FROM faq_chunks ORDER BY embedding <=> '[0.1, ...]' LIMIT 5;
# 建 HNSW（43 筆秒建；100k 數據用簡報截圖講）
CREATE INDEX idx_faq_embedding ON faq_chunks USING hnsw (embedding vector_cosine_ops);
EXPLAIN ANALYZE ...  -- Index Scan using idx_faq_embedding
```

> psql 的 EXPLAIN 需要一個真實向量字串，太長不適合手打——demo 前先把兩條
> EXPLAIN 指令存在 `~/demo_snippets.sql`，現場 `\i demo_snippets.sql` 執行。

## 故障應變表

| 狀況 | 應變 | 演講話術 |
| --- | --- | --- |
| 會場 WiFi 掛 | 切手機熱點重連 SSH（tmux 保留狀態） | 「趁重連，我們看一下架構圖」 |
| SSH 完全上不去 | 切筆電本機 compose 環境 | 無縫，指令完全相同 |
| Ollama LLM 卡住/太慢 | `chatbot.py --no-llm` 只秀檢索；LLM 段播 demo1.mp4 | 「LLM 生成不是今天的重點，檢索層才是」 |
| MySQL 容器掛 | `docker compose restart mysql`（約 20 秒） | 先講 pgvector 段，回頭再 demo |
| 投影訊號問題 | 全程可降級為預錄影片 + 口述 | 影片在本機與手機各一份 |
| 時間嚴重落後 | 依 talk-design 的裁切表：先砍 MyVector live、再砍 chatbot 第 2 題 | 決策框架絕不砍 |

## 收尾（Q&A 前最後一頁停留）

最後一頁固定停在：repo QR code + 三岔路決策圖縮圖 + 聯絡方式（綠豆湯 / litotom）。
Q&A 冷場備援：自問自答「有人會問 MariaDB 嗎？」（答案在 talk-design 預想問題 5）。
