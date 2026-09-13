# COSCUP 2026 · MySQL RAG demo
# Typical flow: make up → make dataset → make ingest → make chat

SHELL := /bin/bash
PY    := python3

up:            ## Start MySQL + pgvector
	docker compose up -d mysql pg

up-ai:         ## Start with Ollama and pull models
	docker compose --profile ai up -d
	docker exec rag-ollama ollama pull bge-m3
	docker exec rag-ollama ollama pull qwen3:4b

down:          ## Stop all services (keep data)
	docker compose --profile ai down

deps:          ## Install Python dependencies
	$(PY) -m pip install -r app/requirements.txt

dataset:       ## Generate the knowledge base and evaluation questions
	cd data && $(PY) generate_faq.py

ingest:        ## Embed + write to both databases
	cd app && $(PY) ingest.py

chat:          ## AI support, interactive mode (MySQL retrieval)
	cd app && $(PY) chatbot.py

chat-pg:       ## AI support, interactive mode (pgvector retrieval)
	cd app && $(PY) chatbot.py --db pg

bench-10k:     ## 10k-row benchmark
	cd app && $(PY) bench.py --scale 10000 --out ../bench/results-10k.csv

bench-100k:    ## 100k-row benchmark
	cd app && $(PY) bench.py --scale 100000 --out ../bench/results-100k.csv

pg-index:      ## Create the pgvector HNSW index by hand
	docker exec rag-pg psql -U postgres -d ragdemo -c \
	  "CREATE INDEX IF NOT EXISTS idx_faq_embedding ON faq_chunks USING hnsw (embedding vector_cosine_ops);"

mysql-cli:     ## Open the MySQL CLI
	docker exec -it rag-mysql mysql -uroot -pcoscup2026 ragdemo

psql-cli:      ## Open the psql CLI
	docker exec -it rag-pg psql -U postgres -d ragdemo

help:
	@grep -E '^[a-zA-Z0-9_-]+:.*##' Makefile | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'
