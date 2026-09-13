#!/usr/bin/env python3
"""Top-K similarity search on MySQL.

Community MySQL has neither DISTANCE() nor an ANN index, so the strategy is:
  1. (optional) coarse-filter candidates in SQL with metadata (category)
  2. pull candidate VECTOR columns as raw binary (4 bytes/dim float32)
  3. score cosine similarity in NumPy and take Top-K

That is the talk's core claim: MySQL is the vector store; distance is computed in the app.

Usage:
    python search_mysql.py "How long until my refund arrives?"
    python search_mysql.py "How long until my refund arrives?" --category Returns --k 5
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
        # Metadata coarse filter: the most effective way to cut work on Community MySQL
        cur.execute("SELECT id, doc_id, title, content, embedding "
                    "FROM faq_chunks WHERE category = %s", (category,))
    else:
        cur.execute("SELECT id, doc_id, title, content, embedding FROM faq_chunks")
    rows = cur.fetchall()
    t_fetch = time.perf_counter() - t0

    if not rows:
        return []

    # VECTOR comes back as float32 binary — frombuffer it; do not use VECTOR_TO_STRING
    mat = np.frombuffer(b"".join(r[4] for r in rows), dtype=np.float32)
    mat = mat.reshape(len(rows), config.EMBED_DIM)

    t1 = time.perf_counter()
    scores = mat @ qv                        # normalized vectors → dot product = cosine
    idx = np.argsort(-scores)[:k]
    t_rank = time.perf_counter() - t1

    hits = [{"id": rows[i][0], "doc_id": rows[i][1], "title": rows[i][2],
             "content": rows[i][3], "score": float(scores[i])} for i in idx]

    if verbose:
        print(f"[MySQL] {len(rows)} candidates | fetch {t_fetch*1000:.1f} ms | "
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
