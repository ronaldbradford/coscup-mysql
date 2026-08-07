#!/usr/bin/env python3
"""MySQL 端的 Top-K 相似度檢索。

社群版 MySQL 沒有 DISTANCE() 也沒有 ANN 索引，所以策略是：
  1.（可選）先用 metadata（category）在 SQL 端粗過濾，縮小候選集
  2. 把候選列的 VECTOR 以「原始 binary」拉回應用端（4 bytes/維 float32）
  3. 用 NumPy 一次算完 cosine 相似度，排序取 Top-K

這正是本場演講的核心論點：MySQL 當「向量儲存層」，距離計算在應用端。

用法：
    python search_mysql.py "退款多久會到？"
    python search_mysql.py "退款多久會到？" --category 退換貨 --k 5
"""
import argparse
import time

import mysql.connector
import numpy as np

import config
import embedder


def topk(query: str, k: int = 3, category: str | None = None, verbose: bool = True):
    qv = embedder.embed_one(query)          # (1024,) normalized

    conn = mysql.connector.connect(**config.MYSQL)
    cur = conn.cursor()

    t0 = time.perf_counter()
    if category:
        # metadata 粗過濾：這是社群版 MySQL 最有效的「省算力」手段
        cur.execute("SELECT id, doc_id, title, content, embedding "
                    "FROM faq_chunks WHERE category = %s", (category,))
    else:
        cur.execute("SELECT id, doc_id, title, content, embedding FROM faq_chunks")
    rows = cur.fetchall()
    t_fetch = time.perf_counter() - t0

    if not rows:
        return []

    # VECTOR 欄位讀回來就是 float32 的 binary，可直接 frombuffer——不需要 VECTOR_TO_STRING
    mat = np.frombuffer(b"".join(r[4] for r in rows), dtype=np.float32)
    mat = mat.reshape(len(rows), config.EMBED_DIM)

    t1 = time.perf_counter()
    scores = mat @ qv                        # normalized 向量 → 內積即 cosine 相似度
    idx = np.argsort(-scores)[:k]
    t_rank = time.perf_counter() - t1

    hits = [{"id": rows[i][0], "doc_id": rows[i][1], "title": rows[i][2],
             "content": rows[i][3], "score": float(scores[i])} for i in idx]

    if verbose:
        print(f"[MySQL] 候選 {len(rows)} 列｜fetch {t_fetch*1000:.1f} ms｜"
              f"rank {t_rank*1000:.1f} ms")
        for h in hits:
            print(f"  {h['score']:.4f}  [{h['doc_id']}] {h['title']}")
    cur.close(); conn.close()
    return hits


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--category", default=None)
    args = ap.parse_args()
    topk(args.query, args.k, args.category)
