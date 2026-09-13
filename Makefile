# COSCUP 2026 · MySQL RAG demo
# Typical flow: make up → make dataset → make ingest → make chat

SHELL := /bin/bash
PY    := python3

# qwen3:4b + bge-m3 OOM-killed in a 5.8 GiB Rancher VM; 8 GiB is the floor.
MIN_CHAT_GIB  ?= 8
MIN_CHAT_CPUS ?= 2

check-chat:    ## Verify Docker VM RAM/CPU before launching the LLM
	@info=$$(docker info --format '{{.NCPU}} {{.MemTotal}}' 2>/dev/null) || { \
	  echo "Docker is not running. Start Rancher Desktop (or Docker Desktop), then retry."; \
	  exit 1; \
	}; \
	cpus=$${info%% *}; \
	mem=$${info##* }; \
	if ! [[ $$cpus =~ ^[0-9]+$$ && $$mem =~ ^[0-9]+$$ ]]; then \
	  echo "Could not read Docker VM resources from: $$info"; \
	  exit 1; \
	fi; \
	gib=$$((mem / 1024 / 1024 / 1024)); \
	echo "Docker VM: $$cpus CPUs, $$gib GiB RAM (need >= $(MIN_CHAT_CPUS) CPUs, $(MIN_CHAT_GIB) GiB)"; \
	fail=0; \
	if [ $$cpus -lt $(MIN_CHAT_CPUS) ]; then \
	  echo "Too few CPUs ($$cpus < $(MIN_CHAT_CPUS))."; \
	  echo "Raise Rancher Desktop → Settings → Virtual Machine → CPUs."; \
	  fail=1; \
	fi; \
	if [ $$gib -lt $(MIN_CHAT_GIB) ]; then \
	  echo "Not enough RAM ($$gib GiB < $(MIN_CHAT_GIB) GiB). qwen3:4b will be OOM-killed."; \
	  echo "Raise Rancher Desktop → Settings → Virtual Machine → Memory to at least $(MIN_CHAT_GIB) GiB (12+ recommended)."; \
	  echo "Or skip the LLM:  cd app && $(PY) chatbot.py --no-llm"; \
	  echo "Or use a smaller model:  LLM_MODEL=qwen3:1.7b make chat"; \
	  fail=1; \
	fi; \
	exit $$fail

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

chat: check-chat ## AI support, interactive mode (MySQL retrieval)
	cd app && $(PY) chatbot.py

chat-pg: check-chat ## AI support, interactive mode (pgvector retrieval)
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
