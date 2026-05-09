# 從零打造一個 MySQL-based RAG 系統

**VECTOR 型別實戰、工程取捨與 pgvector 對照**

> Building a RAG System on MySQL from Scratch — VECTOR Type in Practice, Engineering Trade-offs, and a pgvector Reference

本 repo 為 **COSCUP 2026 MySQL 軌**同名議程的搭配資源，收錄完整 demo 程式碼、SQL schema、benchmark 腳本與投影片原始檔。

- 議程：COSCUP 2026, MySQL Track（2026 年 8 月）
- 講者：Hank
- 程式碼授權：Apache-2.0
- 內容（slides、文件）授權：CC BY-SA 4.0

---

## Abstract

當大家談到 RAG（Retrieval-Augmented Generation），第一個想到的儲存層往往是 Pinecone、Qdrant、Milvus，或是 PostgreSQL + pgvector。但是在絕大多數企業既有的 stack 裡，MySQL 才是那個「明明就在那裡、卻幾乎沒有人在 RAG 選型討論中提到」的角色。

MySQL 9.0 已經正式加入 `VECTOR` 資料型別。那麼問題來了:在不另外搬一座資料庫的前提下,到底能不能用 MySQL 把一個可運作的 RAG 系統做出來?做得起來、又能撐多久?

本場次以一個從零打造、完整開源的 demo 專案為主軸,帶聽眾一步步在 MySQL 9.x 上構建 RAG 系統:從 schema 設計、embedding 寫入、Top-K 相似度查詢,到串接 LLM 完成問答。途中會深入 `VECTOR` 型別的內部儲存方式、可用函式,以及目前最關鍵的限制——社群版尚未提供原生 ANN 索引。

接著,我們把同一份資料、同一組查詢搬到 PostgreSQL pgvector 上做對照組 benchmark,誠實呈現兩者在 latency、recall、開發體驗、維運成本上的差距。最後提出一個務實的選型決策框架:什麼情境下「在 MySQL 上做 RAG」是合理的工程選擇,什麼情境下應該果斷換工具。

所有 demo 程式碼、SQL schema、benchmark 腳本與投影片都會以 Apache-2.0 / CC BY-SA 授權公開於本 repo,現場聽眾可以即時在自己的環境重現。

---

## 預期聽眾收穫

1. 理解 MySQL `VECTOR` 型別的能力邊界與內部實作。
2. 帶走一份可在自己環境跑起來的 RAG demo 專案（Docker Compose 一鍵啟動）。
3. 一份 MySQL vs pgvector 的功能與效能對照表。
4. 一個務實的「該不該在 MySQL 上做 RAG」選型決策框架。

## 目標聽眾

DBA、後端工程師、SRE，以及對 RAG 有興趣但不確定資料庫選型的工程師。難度為中階——需要基本 SQL 與 LLM／embedding 概念，不需要懂 ML 訓練。

---

## Repo 結構（規劃中）

```
.
├── mysql/        # MySQL 9.x 端的 schema、ingestion、query
├── pgvector/     # PostgreSQL + pgvector 對照組
├── bench/        # benchmark 腳本與結果（CSV + 圖）
├── slides/       # 投影片原始檔
├── docs/         # 文章版說明、決策框架、對照表
└── docker-compose.yml
```

## 快速開始（規劃中）

```bash
git clone <repo-url>
cd <repo>
docker compose up -d
make ingest
make bench
```

> 詳細指引將於議程前完成並補上。

---

## 授權

- 程式碼：[Apache-2.0](LICENSE)
- 內容（slides、docs）：[CC BY-SA 4.0](LICENSE-CONTENT)

引用時請註明來源並保留授權標示。
