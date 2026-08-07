#!/usr/bin/env python3
"""Benchmark：同資料、同查詢，MySQL（app-side 全掃描）vs pgvector（seq scan / HNSW）。

情境：
  mysql_full      — MySQL 全表拉回 + NumPy cosine（無 metadata 過濾）
  mysql_filtered  — MySQL 先以 category 過濾（約砍到 1/10）再 app-side 排序
  pg_seq          — pgvector 無索引（exact，seq scan）
  pg_hnsw         — pgvector HNSW 索引（ANN）

用法：
    python bench.py --scale 10000 --queries 30
    python bench.py --scale 100000 --queries 30 --out ../bench/results-100k.csv
"""
import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

import mysql.connector
import numpy as np
import psycopg2

import config
import embedder

sys.path.insert(0, str(Path(__file__).parent.parent / "data"))
from generate_faq import FILLER_TOPICS, make_filler  # noqa: E402

QUERIES = ["退款多久會入帳", "超商取貨過期沒領", "刷卡一直失敗怎麼辦", "購物金有效期限",
           "發票想打統編", "包裹顯示送達但沒收到", "會員等級的優惠", "折扣碼不能用",
           "尺寸不合想換貨", "帳號被盜用了"]


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * p / 100))]


def fill_dbs(n):
    """把知識庫擴充到 n 筆（含 filler），同步寫入兩座 DB。"""
    print(f"產生 {n} 筆 filler 與 embedding（backend={config.EMBED_BACKEND}）...")
    rows = []
    fillers = make_filler(n)
    B = 512
    for i in range(0, len(fillers), B):
        batch = fillers[i:i + B]
        vecs = embedder.embed([c["content"] for c in batch])
        rows += [(c["id"], c["category"], c["title"], c["content"],
                  embedder.to_vector_literal(v)) for c, v in zip(batch, vecs)]
        print(f"  embed {min(i+B, n)}/{n}", end="\r")
    print()

    my = mysql.connector.connect(**config.MYSQL); mc = my.cursor()
    mc.execute("DELETE FROM faq_chunks WHERE doc_id LIKE 'filler-%'")
    sql_my = ("INSERT INTO faq_chunks (doc_id, category, title, content, embedding) "
              "VALUES (%s,%s,%s,%s,STRING_TO_VECTOR(%s))")
    t0 = time.perf_counter()
    for i in range(0, len(rows), 1000):
        mc.executemany(sql_my, rows[i:i + 1000]); my.commit()
        print(f"  MySQL insert {min(i+1000, len(rows))}/{len(rows)}", end="\r")
    print(f"\n  MySQL 寫入 {time.perf_counter()-t0:.1f}s")
    mc.close(); my.close()

    pg = psycopg2.connect(config.PG_DSN); pc = pg.cursor()
    pc.execute("DROP INDEX IF EXISTS idx_faq_embedding")
    pc.execute("DELETE FROM faq_chunks WHERE doc_id LIKE 'filler-%'")
    sql_pg = ("INSERT INTO faq_chunks (doc_id, category, title, content, embedding) "
              "VALUES (%s,%s,%s,%s,%s::vector)")
    t0 = time.perf_counter()
    for i in range(0, len(rows), 1000):
        pc.executemany(sql_pg, rows[i:i + 1000]); pg.commit()
        print(f"  pg insert {min(i+1000, len(rows))}/{len(rows)}", end="\r")
    print(f"\n  pgvector 寫入 {time.perf_counter()-t0:.1f}s")
    pc.close(); pg.close()


def bench_mysql(qvecs, category=None):
    conn = mysql.connector.connect(**config.MYSQL); cur = conn.cursor()
    lat = []
    for qv in qvecs:
        t0 = time.perf_counter()
        if category:
            cur.execute("SELECT id, embedding FROM faq_chunks WHERE category=%s", (category,))
        else:
            cur.execute("SELECT id, embedding FROM faq_chunks")
        rows = cur.fetchall()
        mat = np.frombuffer(b"".join(r[1] for r in rows), dtype=np.float32)
        mat = mat.reshape(len(rows), config.EMBED_DIM)
        np.argsort(-(mat @ qv))[:5]
        lat.append((time.perf_counter() - t0) * 1000)
    cur.close(); conn.close()
    return lat, len(rows)


def bench_pg(qvecs, hnsw: bool):
    conn = psycopg2.connect(config.PG_DSN); cur = conn.cursor()
    if hnsw:
        print("  建立 HNSW 索引（build time 也是成本，計入報告）...")
        t0 = time.perf_counter()
        cur.execute("SET maintenance_work_mem='1GB'")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_faq_embedding ON faq_chunks "
                    "USING hnsw (embedding vector_cosine_ops)")
        conn.commit()
        print(f"  HNSW build: {time.perf_counter()-t0:.1f}s")
    else:
        cur.execute("DROP INDEX IF EXISTS idx_faq_embedding"); conn.commit()
    lat = []
    for qv in qvecs:
        lit = embedder.to_vector_literal(qv)
        t0 = time.perf_counter()
        cur.execute("SELECT id FROM faq_chunks ORDER BY embedding <=> %s::vector LIMIT 5",
                    (lit,))
        cur.fetchall()
        lat.append((time.perf_counter() - t0) * 1000)
    cur.close(); conn.close()
    return lat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=10000)
    ap.add_argument("--queries", type=int, default=30)
    ap.add_argument("--skip-fill", action="store_true", help="資料已在庫，直接測")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if not args.skip_fill:
        fill_dbs(args.scale)

    qs = (QUERIES * (args.queries // len(QUERIES) + 1))[:args.queries]
    qvecs = embedder.embed(qs)

    results = []
    print(f"\n=== Benchmark @ {args.scale} rows, {args.queries} queries ===")
    lat, nrows = bench_mysql(qvecs)
    results.append(("mysql_full", lat, f"{nrows} rows scanned"))
    cat = FILLER_TOPICS[0]
    lat, nrows = bench_mysql(qvecs, category=cat)
    results.append(("mysql_filtered", lat, f"category={cat}, {nrows} rows"))
    lat = bench_pg(qvecs, hnsw=False)
    results.append(("pg_seq", lat, "exact / seq scan"))
    lat = bench_pg(qvecs, hnsw=True)
    results.append(("pg_hnsw", lat, "ANN / HNSW"))

    print(f"\n{'scenario':<16}{'p50 (ms)':>10}{'p95 (ms)':>10}{'mean':>10}   note")
    for name, lat, note in results:
        print(f"{name:<16}{pct(lat,50):>10.1f}{pct(lat,95):>10.1f}"
              f"{statistics.mean(lat):>10.1f}   {note}")

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["scenario", "scale", "p50_ms", "p95_ms", "mean_ms", "note"])
            for name, lat, note in results:
                w.writerow([name, args.scale, f"{pct(lat,50):.1f}",
                            f"{pct(lat,95):.1f}", f"{statistics.mean(lat):.1f}", note])
        print(f"\n結果已寫入 {args.out}")


if __name__ == "__main__":
    main()
