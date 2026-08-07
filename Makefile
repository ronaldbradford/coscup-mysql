# COSCUP 2026 · MySQL RAG demo
# 常用：make up → make dataset → make ingest → make chat

SHELL := /bin/bash
PY    := python3

up:            ## 啟動 MySQL + pgvector
	docker compose up -d mysql pg

up-ai:         ## 連同 Ollama 一起啟動，並拉模型
	docker compose --profile ai up -d
	docker exec rag-ollama ollama pull bge-m3
	docker exec rag-ollama ollama pull qwen3:4b

down:          ## 停止所有服務（保留資料）
	docker compose --profile ai down

deps:          ## 安裝 Python 相依
	$(PY) -m pip install -r app/requirements.txt

dataset:       ## 產生知識庫與評估問句
	cd data && $(PY) generate_faq.py

ingest:        ## embedding + 寫入兩座資料庫
	cd app && $(PY) ingest.py

chat:          ## AI 客服互動模式（MySQL 檢索）
	cd app && $(PY) chatbot.py

chat-pg:       ## AI 客服互動模式（pgvector 檢索）
	cd app && $(PY) chatbot.py --db pg

bench-10k:     ## 一萬筆 benchmark
	cd app && $(PY) bench.py --scale 10000 --out ../bench/results-10k.csv

bench-100k:    ## 十萬筆 benchmark
	cd app && $(PY) bench.py --scale 100000 --out ../bench/results-100k.csv

pg-index:      ## 手動建立 pgvector HNSW 索引
	docker exec rag-pg psql -U postgres -d ragdemo -c \
	  "CREATE INDEX IF NOT EXISTS idx_faq_embedding ON faq_chunks USING hnsw (embedding vector_cosine_ops);"

mysql-cli:     ## 進入 MySQL CLI
	docker exec -it rag-mysql mysql -uroot -pcoscup2026 ragdemo

psql-cli:      ## 進入 psql CLI
	docker exec -it rag-pg psql -U postgres -d ragdemo

help:
	@grep -E '^[a-zA-Z0-9_-]+:.*##' Makefile | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'
