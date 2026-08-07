#!/usr/bin/env python3
"""綠豆選物 AI 客服 —— RAG 問答迴圈（demo 主秀）。

流程：使用者問題 → embedding → Top-K 檢索（MySQL 或 pgvector）
      → 組 prompt（附知識庫內容與來源）→ Ollama LLM 生成繁中回答

用法：
    python chatbot.py                  # 互動模式，預設檢索 MySQL
    python chatbot.py --db pg          # 改用 pgvector 檢索
    python chatbot.py --no-llm         # 只看檢索結果不叫 LLM（測試用）
    python chatbot.py -q "刷卡失敗怎麼辦"   # 單發模式
"""
import argparse
import json
import sys

import requests

import config
import search_mysql
import search_pg

SYSTEM = """你是台灣電商「綠豆選物」的 AI 客服。請遵守：
1. 只根據提供的〈知識庫〉內容回答，知識庫沒有的資訊要誠實說「這個問題我需要為您轉接真人客服」。
2. 用台灣慣用的繁體中文，語氣親切、精簡，條列重點。
3. 回答結尾標註引用的知識庫編號，例如（參考：return-004）。"""


def build_prompt(question: str, hits: list[dict]) -> str:
    ctx = "\n\n".join(f"[{h['doc_id']}] {h['content']}" for h in hits)
    return f"〈知識庫〉\n{ctx}\n\n〈顧客問題〉\n{question}"


def ask_llm(question: str, hits: list[dict]):
    resp = requests.post(
        f"{config.OLLAMA_URL}/api/chat",
        json={
            "model": config.LLM_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": build_prompt(question, hits)},
            ],
            "stream": True,
            "options": {"temperature": 0.3},
        },
        stream=True, timeout=600,
    )
    resp.raise_for_status()
    print("\n🤖 綠豆選物客服：", end="", flush=True)
    for line in resp.iter_lines():
        if not line:
            continue
        piece = json.loads(line)
        print(piece.get("message", {}).get("content", ""), end="", flush=True)
        if piece.get("done"):
            break
    print("\n")


def answer(question: str, db: str, k: int, use_llm: bool):
    retriever = search_pg.topk if db == "pg" else search_mysql.topk
    hits = retriever(question, k=k, verbose=True)
    if not hits:
        print("（檢索不到任何內容，請先執行 ingest.py）")
        return
    if use_llm:
        ask_llm(question, hits)
    else:
        print("--- 檢索到的知識庫內容（--no-llm 模式）---")
        for h in hits:
            print(f"\n[{h['doc_id']}] score={h['score']:.4f}\n{h['content'][:120]}...")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["mysql", "pg"], default="mysql")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("-q", "--question", default=None)
    args = ap.parse_args()

    if args.question:
        answer(args.question, args.db, args.k, not args.no_llm)
        return

    print(f"=== 綠豆選物 AI 客服（檢索：{args.db}，Ctrl-C 離開）===")
    while True:
        try:
            q = input("\n💬 請輸入問題：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再見！")
            break
        if q:
            answer(q, args.db, args.k, not args.no_llm)


if __name__ == "__main__":
    sys.exit(main())
