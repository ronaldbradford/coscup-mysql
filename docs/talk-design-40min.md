# COSCUP 2026 專題設計（40 分鐘版）

**從零打造一個 MySQL-based RAG 系統：VECTOR 型別實戰、工程取捨與 pgvector 對照**

> 講者：Hank（綠豆湯 / litotom）｜MySQL 軌｜40 分鐘（含 Q&A 約 3 分鐘）

---

## 核心敘事（一句話）

用「綠豆選物」電商 AI 客服這個具體案例，誠實回答一個問題：**「公司只有 MySQL，能不能不搬資料庫就把 RAG 做起來？」**——答案是「能，但要知道自己在做什麼」，並以 pgvector 對照與三岔路決策框架收尾。

### 為什麼用 AI 客服當案例（設計依據）

1. **人人聽得懂**：不用解釋業務背景，觀眾 10 秒進入狀況；問答互動天生適合 live demo。
2. **天生就是 RAG**：客服知識庫（FAQ、退貨政策、物流規則）就是典型的檢索語料；「客人用一百種問法問同一件事」正是向量檢索存在的理由，可以現場示範關鍵字搜尋 vs 語意搜尋的差異。
3. **資料完全可控**：知識庫是為本 demo 合成的虛構電商「綠豆選物 LitoShop」資料（43 個知識 chunk、173 句改寫問句、可擴增至 10 萬筆），CC0 授權、無個資、無版權疑慮，完全符合 COSCUP 開放授權審查。
4. **規模故事好講**：真實客服庫幾百～幾千條，MySQL 全掃描也夠用（demo I 的甜蜜點）；但引入商品庫、對話歷史後上看數十萬向量，就進入深水區（benchmark 的敘事跳板）。

### 三幕劇結構

| 幕 | 訊息 | 情緒 |
| --- | --- | --- |
| 第一幕：能做 | MySQL 9.x 存 VECTOR、app-side 算距離，AI 客服跑起來了 | 「哦！真的可以」 |
| 第二幕：代價 | 沒有 DISTANCE()、沒有 ANN，100k 筆時 2 秒 vs pgvector 10ms | 「原來差這麼多」 |
| 第三幕：選擇 | metadata 過濾、MyVector 外掛、或換 pgvector——決策框架 | 「我知道怎麼選了」 |

---

## 40 分鐘逐段流程

### 00:00–03:00｜開場：綠豆選物要上 AI 客服（3 分）

- 自我介紹 30 秒（綠豆湯部落格、30 年開發資歷，一頁帶過）。
- Hook：虛構情境——電商「綠豆選物」客服每天被問「退款多久會到」一百次，每次問法都不一樣。要上 AI 客服，架構師說要加一座向量資料庫，DBA 說「我們不是有 MySQL 嗎？」→ 這場演講就是這場會議的完整技術答辯。
- 範圍宣告：不講 LLM 訓練、不講向量數學、不碰 HeatWave 專屬功能。

### 03:00–07:00｜RAG 101 與「為什麼是 MySQL」（4 分）

- 一頁講完 RAG：問題 → embedding → 相似度檢索 Top-K → 塞進 prompt → LLM 回答。強調本場焦點只在「檢索層的資料庫」。
- 選型現況：大家先想到 Pinecone/Qdrant/Milvus/pgvector，沒人提 MySQL——但 MySQL 是企業既有 stack 裡最常見的 OLTP DB。「不搬資料、不加維運面、交易資料就在旁邊 JOIN」是真實的工程誘因。

### 07:00–12:00｜MySQL VECTOR 現況解密（5 分）

- `VECTOR(N)` 型別：9.0 引入，4 bytes/維 float32 binary，上限 16383 維。
- 社群版真正擁有的函式只有四個之三：`STRING_TO_VECTOR`、`VECTOR_TO_STRING`、`VECTOR_DIM`。
- **現場梗（重要）**：live 執行 `SELECT DISTANCE(...)` → `ERROR 1305 FUNCTION DISTANCE does not exist`。官方文件寫著「HeatWave on OCI only」。9.7（2026-04 GA）依然如此，vector search 仍在 roadmap 上。
- 結論鋪陳：型別有了、引擎沒給——「車給了你座椅和方向盤，引擎要自己想辦法」。這就是接下來 demo 的架構前提。

### 12:00–20:00｜Live Demo I：AI 客服 on MySQL（8 分）

- 架構圖 30 秒：問題 → Ollama bge-m3 embedding → MySQL 檢索 → Ollama qwen3 生成 → 回答（全開源、全本地）。
- Schema 講解（1 分）：`faq_chunks(doc_id, category, title, content, embedding VECTOR(1024))`；`category` 索引是後面的伏筆。
- 檢索策略講解（2 分）：候選列以「原始 binary」拉回 → `np.frombuffer` → 內積排序。強調「embedding 已 normalize，cosine = dot product」。
- Live：`python search_mysql.py "退款多久會到？"`——語意檢索命中 return-004，即使問法完全不同（1.5 分）。
- Live：`python chatbot.py` 問 2 題（3 分）：
  - 「我上週買的衣服想換大一號，要收費嗎？」→ 命中 return-005，回答含免費換貨一次。
  - 「接到電話叫我去 ATM 解除分期」→ 命中 account-001，回答提醒 165 反詐騙——展示 RAG 讓 LLM 說「對的話」。
- 小結：500 條知識庫、43 chunk，MySQL 檢索 2-3ms——**在這個規模，它就是夠用**。

### 20:00–25:00｜工程深水區：沒有 ANN 的代價（5 分）

- 提問轉場：「知識庫長到 10 萬筆呢？」（加入商品說明、歷史工單）。
- Benchmark 圖（本 repo `bench/` 可重現；以下為 7GB RAM 容器實測，現場請以 VM 數據為準）：

  | 情境 | 10k 筆 p50 | 100k 筆 p50 |
  | --- | --- | --- |
  | MySQL 全掃描 + app-side | 242 ms | 2,144 ms |
  | MySQL category 過濾（1/10） | 38 ms | 244 ms |
  | pgvector 無索引（exact） | 39 ms | 469 ms |
  | pgvector HNSW | 2.2 ms | 9.7 ms |

- 解讀：全掃描的成本是「每次查詢搬 400MB 出資料庫」；瓶頸在網路與反序列化，不在 NumPy。
- 規避術（MySQL 陣營還能怎麼撐）：metadata 粗過濾（客服場景天然有 category／tenant 維度，一刀砍 90% 候選）、partition by tenant、限縮 TOP-K 候選的覆蓋索引、read replica 分流。
- 誠實結論：這些都是「延後失守」，不是 ANN 的替代品。

### 25:00–30:00｜Live Demo II：pgvector 對照組（5 分）

- 同一份資料、同一支 chatbot，`--db pg` 一個參數切換。
- 展示 SQL 的差異：`ORDER BY embedding <=> :q LIMIT 5`——距離計算與排序都在 DB 內。
- Live：`EXPLAIN ANALYZE` 建 HNSW 索引前後對比（seq scan → Index Scan using hnsw）。
- 一頁對照表：型別/維度上限、距離函式、索引、過濾互動（0.8 的 iterative scan）、生態（halfvec、量化）。
- 提醒：pgvector 也不是免費午餐——HNSW build time 與記憶體、ANN 的 recall 取捨、多一座資料庫的維運成本。

### 30:00–33:00｜第三條路：MyVector（3 分）

- 社群自己造引擎：MyVector plugin（GPLv2，開源），HNSW ANN 直接進 MySQL，binlog 同步索引，支援 8.0/8.4/9.7。
- 一頁 SQL 範例：`MYVECTOR(type=HNSW,dim=1024)` 欄位註記 + `MYVECTOR_IS_ANN(...)` 查詢。
- 定位：證明「MySQL 生態不是沒人管」，但 plugin 的採用風險（升級、支援、社群規模）要自行評估。時間充裕才 live（備選 demo），否則以投影片與預錄畫面帶過。

### 33:00–37:00｜決策框架與總結（4 分）

- 三岔路決策圖：
  - **留在 MySQL**：向量 < 5 萬、QPS 低、有天然過濾維度、不想加維運面——app-side 檢索完全成立。
  - **MySQL + MyVector**：想留在 MySQL 又需要 ANN，能接受第三方 plugin 的風險。
  - **搬到 pgvector / 專用向量 DB**：規模、延遲、recall 是硬需求，或團隊本來就有 PG。
- 帶走的三件事：一份可 `docker compose up` 重現的 AI 客服 demo、一張 MySQL vs pgvector 對照表、一個選型決策框架。
- Repo QR code（Apache-2.0 / CC BY-SA 4.0）＋「到 MySQL 官方把 vector search 投上 roadmap」的社群共好結尾。

### 37:00–40:00｜Q&A（3 分）

預想問題與準備答案：

1. 「為什麼不直接用 JSON 存向量？」→ VECTOR 省空間（4B/維 vs 文字）、有型別檢查；但檢索策略相同。
2. 「HeatWave 不就有 DISTANCE？」→ 有，但那是 OCI 雲服務，不是你機房裡的社群版；本場只談開源可得的能力。
3. 「embedding 模型換了怎麼辦？」→ 維度變更需要 rebuild 欄位與全量重算，兩邊都一樣痛，schema 設計時把 model 版本記進 metadata。
4. 「中文檢索品質？」→ bge-m3 多語表現佳；正式系統建議加 rerank 層，本場範圍外。
5. 「MariaDB 呢？」→ MariaDB 11.7 有自己的 VECTOR 與 HNSW 索引，值得關注，但那是另一場演講。

---

## 時間風險控制

| 檢查點 | 應在時間 | 落後時的裁切 |
| --- | --- | --- |
| Demo I 結束 | 20:00 | chatbot 只問 1 題（砍 1.5 分） |
| Benchmark 講完 | 25:00 | 規避術只講 metadata 過濾（砍 1 分） |
| Demo II 結束 | 30:00 | EXPLAIN 用截圖不 live（砍 1.5 分） |
| MyVector 結束 | 33:00 | 整段可縮成 1 頁 1 分鐘（砍 2 分） |

原則：**決策框架（33:00–37:00）絕不裁切**——它是聽眾帶走的核心價值；MyVector 是彈性最大的緩衝段。
