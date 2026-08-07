"""共用設定：由環境變數覆寫，預設值對應 docker-compose.yml。"""
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

# embedding：bge-m3（MIT 授權，多語系表現佳，1024 維）
# EMBED_BACKEND=fake 時使用「確定性假向量」——沒有 GPU / 沒拉模型也能跑通整個流程
EMBED_BACKEND = os.getenv("EMBED_BACKEND", "ollama")   # ollama | fake
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))

LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:4b")
