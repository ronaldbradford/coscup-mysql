# Building a MySQL-based RAG System from Scratch

**VECTOR Type in Practice, Engineering Trade-offs, and a pgvector Comparison**

This repo is companion material for the **COSCUP 2026 MySQL track** talk of the same name. It includes the full demo code, SQL schemas, benchmark scripts, and slide sources.

- Talk: COSCUP 2026, MySQL Track (August 2026)
- Speaker: Hank
- Code license: Apache-2.0
- Content (slides, docs) license: CC BY-SA 4.0

---

## Abstract

When people talk about RAG (Retrieval-Augmented Generation), the first storage layers that come to mind are usually Pinecone, Qdrant, Milvus, or PostgreSQL + pgvector. In most existing enterprise stacks, though, MySQL is the database that is already there — and almost never mentioned in RAG architecture discussions.

MySQL 9.0 officially added the `VECTOR` data type. So the question is: without standing up another database, can you actually build a working RAG system on MySQL? And if you can, how far will it go?

This session walks through a from-scratch, fully open-source demo: building a RAG system on MySQL 9.x step by step — schema design, writing embeddings, Top-K similarity search, and wiring up an LLM for Q&A. Along the way we look at how the `VECTOR` type is stored internally, which functions are available, and the most important current limitation: Community Edition still has no native ANN index.

Then we move the same data and the same queries onto PostgreSQL pgvector as a control-group benchmark, and show the honest gaps in latency, recall, developer experience, and operational cost. We close with a practical decision framework: when “do RAG on MySQL” is a reasonable engineering choice, and when you should switch tools.

All demo code, SQL schemas, benchmark scripts, and slides will be published in this repo under Apache-2.0 / CC BY-SA, so attendees can reproduce the setup in their own environment.

---

## What you will take away

1. The capability bounds and internals of MySQL’s `VECTOR` type.
2. A RAG demo you can run in your own environment (one-command Docker Compose).
3. A MySQL vs pgvector feature and performance comparison.
4. A practical “should we do RAG on MySQL?” decision framework.

## Who this is for

DBAs, backend engineers, SREs, and anyone interested in RAG who is unsure about database choice. Intermediate level — you need basic SQL and LLM / embedding concepts, not ML training experience.

---

## Demo scenario

AI customer support for a fictional store, **LitoShop**. The knowledge base is a synthetic English e-commerce support FAQ
(43 knowledge chunks / 10 categories / 173 paraphrase evaluation questions, CC0, no PII or copyright issues).
The benchmark can scale to 100,000 rows. Dual retrieval backends (MySQL 9.7 / pgvector) switch with one command.

## Repo layout

```
.
├── docker-compose.yml   # MySQL 9.7 + pgvector 0.8 (+ Ollama, profile: ai)
├── Makefile             # make help lists all commands
├── scripts/             # Linux nested-Docker helpers (dual-iptables compose-bridge fix)
├── mysql/init/          # MySQL schema (VECTOR(1024))
├── pgvector/init/       # pgvector schema + HNSW notes
├── app/                 # ingest / search_mysql / search_pg / chatbot / bench
├── data/                # faq_seed.json + generate_faq.py (synthetic knowledge base)
├── bench/               # benchmark results (CSV)
├── slides/              # Marp slide sources + HTML/PDF
└── docs/                # 40-minute session design, setup guide, on-site runbook
```

## Quick start

```bash
git clone <repo-url> && cd <repo>
make up        # MySQL 9.7 + pgvector
make up-ai     # + Ollama (bge-m3 embedding, qwen3:4b LLM)
make deps      # pip install -r app/requirements.txt
make dataset   # generate the knowledge base
make ingest    # embed + write to both databases
make chat      # AI support (MySQL retrieval); make chat-pg switches to pgvector
make bench-10k # benchmark (also bench-100k)
```

> No GPU / don’t want to pull models? `EMBED_BACKEND=fake` runs the full pipeline with deterministic fake vectors
> (zero semantic quality, but the flow and performance characteristics are equivalent — good for CI and a quick smoke test).
>
> Detailed guides: `docs/environment-setup.md` (VM setup), `docs/runbook.md` (talk-day operations).

---

## License

- Code: [Apache-2.0](LICENSE)
- Content (slides, docs): [CC BY-SA 4.0](LICENSE-CONTENT)

Please attribute the source and keep the license notice when you reuse this material.
