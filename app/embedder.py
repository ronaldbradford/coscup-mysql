"""Embedding 產生器：Ollama（bge-m3）或 fake（確定性假向量，供無模型環境測試）。"""
import hashlib

import numpy as np
import requests

import config


def _fake_embed(text: str) -> np.ndarray:
    """以文字 hash 當種子產生固定向量。語意檢索品質為零，但流程與效能特性等價。"""
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
    """回傳 L2 normalized 的 float32 向量（normalized 後 cosine 相似度 = 內積）。"""
    if config.EMBED_BACKEND == "fake":
        return [_fake_embed(t) for t in texts]
    return _ollama_embed(texts)


def embed_one(text: str) -> np.ndarray:
    return embed([text])[0]


def to_vector_literal(v: np.ndarray) -> str:
    """轉成 '[0.1,0.2,...]' 字串——MySQL STRING_TO_VECTOR 與 pgvector 都吃這個格式。"""
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"
