"""Embedding generator: Ollama (bge-m3) or fake (deterministic dummy vectors for model-free tests)."""
import hashlib

import numpy as np
import requests

import config


def _fake_embed(text: str) -> np.ndarray:
    """Fixed vector from a hash of the text. Zero semantic quality; flow and perf characteristics match."""
    seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(config.EMBED_DIM).astype(np.float32)
    return v / np.linalg.norm(v)


def _ollama_embed(texts: list[str]) -> list[np.ndarray]:
    resp = requests.post(
        f"{config.OLLAMA_URL}/api/embed",
        json={"model": config.EMBED_MODEL, "input": texts},
        timeout=300,
    )
    resp.raise_for_status()
    out = []
    for e in resp.json()["embeddings"]:
        v = np.asarray(e, dtype=np.float32)
        out.append(v / np.linalg.norm(v))
    return out


def embed(texts: list[str]) -> list[np.ndarray]:
    """Return L2-normalized float32 vectors (after normalize, cosine = dot product)."""
    if config.EMBED_BACKEND == "fake":
        return [_fake_embed(t) for t in texts]
    return _ollama_embed(texts)


def embed_one(text: str) -> np.ndarray:
    return embed([text])[0]


def to_vector_literal(v: np.ndarray) -> str:
    """'[0.1,0.2,...]' — accepted by both MySQL STRING_TO_VECTOR and pgvector."""
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"
