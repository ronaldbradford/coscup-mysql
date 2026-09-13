#!/usr/bin/env python3
"""Embed knowledge-base chunks from data/faq_dataset.jsonl and write them to MySQL and pgvector.

Usage:
    python ingest.py               # write both databases
    python ingest.py --db mysql    # MySQL only
    python ingest.py --db pg       # pgvector only
"""
import argparse
import json
import sys
import time
from pathlib import Path

import mysql.connector
import psycopg2

import config
import embedder

DATA = Path(__file__).parent.parent / "data" / "faq_dataset.jsonl"
BATCH = 64


def load_chunks():
    with open(DATA, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def ingest_mysql(rows):
    conn = mysql.connector.connect(**config.MYSQL)
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE faq_chunks")
    sql = ("INSERT INTO faq_chunks (doc_id, category, title, content, embedding) "
           "VALUES (%s, %s, %s, %s, STRING_TO_VECTOR(%s))")
    t0 = time.perf_counter()
    cur.executemany(sql, rows)
    conn.commit()
    dt = time.perf_counter() - t0
    cur.close(); conn.close()
    print(f"  MySQL   : {len(rows)} rows in {dt:.2f}s")


def ingest_pg(rows):
    conn = psycopg2.connect(config.PG_DSN)
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE faq_chunks RESTART IDENTITY")
    sql = ("INSERT INTO faq_chunks (doc_id, category, title, content, embedding) "
           "VALUES (%s, %s, %s, %s, %s::vector)")
    t0 = time.perf_counter()
    cur.executemany(sql, rows)
    conn.commit()
    dt = time.perf_counter() - t0
    cur.close(); conn.close()
    print(f"  pgvector: {len(rows)} rows in {dt:.2f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["mysql", "pg", "both"], default="both")
    args = ap.parse_args()

    chunks = load_chunks()
    print(f"Loaded {len(chunks)} knowledge-base chunks; embedding"
          f" (backend={config.EMBED_BACKEND}, model={config.EMBED_MODEL})...")

    rows = []
    t0 = time.perf_counter()
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i + BATCH]
        vecs = embedder.embed([c["content"] for c in batch])
        for c, v in zip(batch, vecs):
            rows.append((c["id"], c["category"], c["title"], c["content"],
                         embedder.to_vector_literal(v)))
        print(f"  embedding {min(i + BATCH, len(chunks))}/{len(chunks)}", end="\r")
    print(f"\nembeddings done: {len(rows)} rows, {time.perf_counter() - t0:.1f}s")

    if args.db in ("mysql", "both"):
        ingest_mysql(rows)
    if args.db in ("pg", "both"):
        ingest_pg(rows)
    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
