"""Shared settings. Override with env vars; defaults match docker-compose.yml."""
import os

MYSQL = dict(
    host=os.getenv("MYSQL_HOST", "127.0.0.1"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", "coscup2026"),
    database=os.getenv("MYSQL_DB", "ragdemo"),
)

PG_DSN = os.getenv(
    "PG_DSN", "host=127.0.0.1 port=5432 user=postgres password=coscup2026 dbname=ragdemo"
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")

# Embedding: bge-m3 (MIT, strong multilingual, 1024 dims)
# EMBED_BACKEND=fake uses deterministic dummy vectors so the pipeline runs without a GPU or pulled models
EMBED_BACKEND = os.getenv("EMBED_BACKEND", "ollama")   # ollama | fake
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))

LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:4b")
