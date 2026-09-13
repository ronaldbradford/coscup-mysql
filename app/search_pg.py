#!/usr/bin/env python3
"""Top-K similarity search on pgvector (the control group).

Distance and ranking happen entirely inside the database:
    ORDER BY embedding <=> %s::vector LIMIT k
With an HNSW index this is ANN; without one it is a seq scan. The demo uses EXPLAIN to show the difference.

Usage:
    python search_pg.py "How long until my refund arrives?"
    python search_pg.py "How long until my refund arrives?" --explain
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
        print(f"[pgvector] query {dt*1000:.1f} ms (distance computed in the DB)")
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
