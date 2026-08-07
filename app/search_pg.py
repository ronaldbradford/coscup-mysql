#!/usr/bin/env python3
"""pgvector 端的 Top-K 相似度檢索（對照組）。

距離計算與排序全部發生在資料庫內：
    ORDER BY embedding <=> %s::vector LIMIT k
有 HNSW 索引時走 ANN，沒有時 seq scan——demo 會用 EXPLAIN 展示差異。

用法：
    python search_pg.py "退款多久會到？"
    python search_pg.py "退款多久會到？" --explain
"""
import argparse
import time

import psycopg2

import config
import embedder


def topk(query: str, k: int = 3, explain: bool = False, verbose: bool = True):
    qv = embedder.embed_one(query)
    lit = embedder.to_vector_literal(qv)

    conn = psycopg2.connect(config.PG_DSN)
    cur = conn.cursor()

    sql = ("SELECT id, doc_id, title, content, embedding <=> %s::vector AS dist "
           "FROM faq_chunks ORDER BY embedding <=> %s::vector LIMIT %s")

    if explain:
        cur.execute("EXPLAIN ANALYZE " + sql, (lit, lit, k))
        print("\n".join(r[0] for r in cur.fetchall()))
        cur.close(); conn.close()
        return []

    t0 = time.perf_counter()
    cur.execute(sql, (lit, lit, k))
    rows = cur.fetchall()
    dt = time.perf_counter() - t0

    hits = [{"id": r[0], "doc_id": r[1], "title": r[2], "content": r[3],
             "score": 1.0 - r[4]} for r in rows]
    if verbose:
        print(f"[pgvector] query {dt*1000:.1f} ms（距離計算在 DB 內完成）")
        for h in hits:
            print(f"  {h['score']:.4f}  [{h['doc_id']}] {h['title']}")
    cur.close(); conn.close()
    return hits


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--explain", action="store_true")
    args = ap.parse_args()
    topk(args.query, args.k, args.explain)
