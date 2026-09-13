#!/usr/bin/env python3
"""LitoShop AI support — the RAG Q&A loop (main demo).

Flow: user question → embedding → Top-K retrieval (MySQL or pgvector)
      → build prompt (knowledge-base text + sources) → Ollama LLM answer

Usage:
    python chatbot.py                       # interactive, MySQL retrieval
    python chatbot.py --db pg               # retrieve from pgvector
    python chatbot.py --no-llm              # retrieval only, no LLM (for testing)
    python chatbot.py -q "card payment failed"
"""
import argparse
import json
import sys

import requests

import config
import search_mysql
import search_pg

SYSTEM = """You are the AI support agent for LitoShop, a Taiwan e-commerce store. Follow these rules:
1. Answer only from the provided <knowledge base>. If it does not contain the answer, say honestly that you need to transfer the customer to a human agent.
2. Write in clear, friendly English. Keep it concise and use bullet points for key facts.
3. End the answer with the knowledge-base IDs you cited, e.g. (source: return-004)."""


def build_prompt(question: str, hits: list[dict]) -> str:
    ctx = "\n\n".join(f"[{h['doc_id']}] {h['content']}" for h in hits)
    return f"<knowledge base>\n{ctx}\n\n<customer question>\n{question}"


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
    print("\n🤖 LitoShop support: ", end="", flush=True)
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
        print("(no matches — run ingest.py first)")
        return
    if use_llm:
        ask_llm(question, hits)
    else:
        print("--- retrieved knowledge-base text (--no-llm) ---")
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

    print(f"=== LitoShop AI support (retrieval: {args.db}, Ctrl-C to quit) ===")
    while True:
        try:
            q = input("\n💬 Your question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if q:
            answer(q, args.db, args.k, not args.no_llm)


if __name__ == "__main__":
    sys.exit(main())
