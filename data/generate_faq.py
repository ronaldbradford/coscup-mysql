#!/usr/bin/env python3
"""Generate the synthetic LitoShop customer-support knowledge base.

Writes two files:
  data/faq_dataset.jsonl  — RAG knowledge base (one chunk per line: id, category, title, content)
  data/eval_queries.jsonl — evaluation queries (query, expected_id) for demo / retrieval-quality checks

Also provides make_filler(n) to pad the benchmark up to N synthetic rows.

License: CC0-1.0 (synthetic data, no real PII)
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).parent

# Query paraphrase templates: customers ask the same thing many ways — that is the RAG problem.
PREFIXES = ["", "Excuse me, ", "Hi, ", "Sorry, ", "Quick question: ", "Urgent! ", "Hello, "]
SUFFIXES = ["", " thanks", " thanks for your help", " please take a look", " waiting"]

REPHRASE = {
    "order-001": ["where is my order now", "how do I see which stage my order is in", "order progress lookup"],
    "order-002": ["I clicked the wrong thing and want to cancel", "I just ordered and already regret it, can I undo it", "can I cancel if it has not shipped yet"],
    "order-003": ["I typed the wrong address, how do I change it", "can I update the recipient details", "I want a different convenience-store pickup"],
    "order-004": ["I have been waiting days and it still has not shipped", "how long until you ship", "why has it not shipped yet"],
    "order-005": ["my order was canceled out of nowhere", "what happens if I do not pick up the package", "my order disappeared by itself"],
    "order-006": ["can two orders ship together", "can you merge shipments", "how do I save on shipping"],
    "ship-001": ["how much is shipping", "what is the free-shipping threshold", "do you have convenience-store pickup", "how long to Penghu"],
    "ship-002": ["track my package", "how do I know where the shipment is", "where do I find the tracking number"],
    "ship-003": ["how many days do I have to pick up a convenience-store order", "do I get penalized if I miss pickup", "the package was returned, what now"],
    "ship-004": ["can I book a delivery time", "can you deliver in the evening", "I am not home during the day, how do I receive it"],
    "ship-005": ["can you ship to Hong Kong", "do you ship abroad", "I live overseas, how can I buy"],
    "ship-006": ["it says delivered but I never got it", "the package is missing", "someone else signed for my order"],
    "return-001": ["how do I return something", "what is the 7-day cooling-off period", "return process"],
    "return-002": ["can I return underwear", "can I return food after opening it", "what cannot be returned"],
    "return-003": ["what I received is broken", "the item is defective, I want a replacement", "it arrived damaged, what now"],
    "return-004": ["when will my refund arrive", "how long until I get my money back", "where does a card refund go"],
    "return-005": ["wrong size, I want to swap it", "can I exchange a wrong color", "does an exchange cost shipping"],
    "return-006": ["what do I do with the invoice on a return", "returning an invoice that has a tax ID", "do I have to mail the invoice back"],
    "pay-001": ["do you take LINE Pay", "do you have cash on delivery", "what payment methods do you accept"],
    "pay-002": ["my card keeps failing", "the credit card will not go through", "why was my payment declined"],
    "pay-003": ["where is the transfer account", "how long is the ATM account valid", "how soon after I transfer is it confirmed"],
    "pay-004": ["can I pay in installments", "is there an installment fee", "does 12 months charge interest"],
    "pay-005": ["I was charged but the order was not created", "I paid but it still says awaiting payment", "I was charged twice, what now"],
    "pay-006": ["I want to switch to card", "can I change the payment method", "I picked the wrong payment method"],
    "invoice-001": ["how do I get an invoice", "will you mail me the invoice", "can I save it to a mobile barcode"],
    "invoice-002": ["I need a company tax ID on the invoice", "I forgot the tax ID, what now", "can you change it to a company invoice"],
    "invoice-003": ["my invoice won, how do I claim it", "will you tell me if I win", "claiming a winning e-invoice"],
    "member-001": ["how do I register", "can I sign in with LINE", "is there a new-member offer"],
    "member-002": ["what is the difference between member tiers", "how do I get to Gold", "what are the Black-tier perks"],
    "member-003": ["how do I use store credit", "does store credit expire", "how much can store credit cover"],
    "member-004": ["I forgot my password", "I cannot sign in", "I did not get the reset email"],
    "member-005": ["I want to delete my account", "how do I close my membership", "do you keep my data after I delete the account"],
    "promo-001": ["where do I claim coupons", "how do I use a discount coupon", "can I stack coupons"],
    "promo-002": ["the discount code does not work", "nothing happens when I enter the code", "the code says it has expired"],
    "promo-003": ["the price dropped right after I bought it", "can I get a price adjustment", "you lowered the price after I paid"],
    "product-001": ["when will you restock", "will an out-of-stock item come back", "can you notify me when it is back"],
    "product-002": ["how do I pick a size", "where is the size chart", "I am 170 cm, should I wear M or L"],
    "product-003": ["will the real color differ from the photos", "does it look like the pictures", "can I return it if I dislike the color"],
    "account-001": ["I got a call claiming to be support", "I got a text telling me to cancel an installment", "is this a scam"],
    "account-002": ["my account was stolen", "there are logins I do not recognize", "there is an order I did not place"],
    "support-001": ["how long is the warranty", "how do I send something in for repair", "does repair cost money"],
    "support-002": ["what is the support phone number", "how do I reach a real person", "what are support hours"],
    "support-003": ["I want to file a complaint", "the service was poor, I want to complain", "where do I send feedback"],
}

# Benchmark filler templates (simulate a larger, noisier knowledge base)
FILLER_TOPICS = ["Orders", "Shipping", "Returns", "Payment", "Invoices", "Membership", "Promotions", "Products", "Account security", "After-sales"]
FILLER_SUBJECTS = ["home delivery", "convenience-store pickup", "credit card", "store credit", "coupon", "e-invoice", "warranty repair",
                   "back-in-stock alert", "installment payment", "member tier", "refund", "exchange", "SMS notification", "account verification"]
FILLER_VERBS = ["look up", "apply for", "cancel", "change", "set up", "use", "extend", "reissue", "link", "unlink"]


def load_seed():
    return json.loads((HERE / "faq_seed.json").read_text(encoding="utf-8"))


def build_dataset():
    seed = load_seed()
    chunks, evals = [], []
    for faq in seed["faqs"]:
        chunks.append({
            "id": faq["id"],
            "category": faq["category"],
            "title": faq["question"],
            "content": f"[{faq['category']}] {faq['question']}\n{faq['answer']}",
        })
        # Original question + paraphrases → evaluation set
        for q in [faq["question"], *REPHRASE.get(faq["id"], [])]:
            evals.append({"query": q, "expected_id": faq["id"], "category": faq["category"]})
    return chunks, evals


def make_filler(n, seed_val=42):
    """Generate n synthetic filler chunks (perf testing only; template combinations)."""
    rng = random.Random(seed_val)
    out = []
    for i in range(n):
        topic = rng.choice(FILLER_TOPICS)
        subj = rng.choice(FILLER_SUBJECTS)
        verb = rng.choice(FILLER_VERBS)
        days = rng.choice([1, 2, 3, 5, 7, 10, 14, 30])
        amount = rng.choice([60, 100, 150, 490, 990, 1500, 3000])
        out.append({
            "id": f"filler-{i:06d}",
            "category": topic,
            "title": f"{verb.title()} {subj} — notes #{i}",
            "content": (f"[{topic}] How to {verb} {subj}: processing usually takes about {days} business days. "
                        f"The related threshold is NT${amount}. See terms clause {rng.randint(1,99)} for details. "
                        f"Contact support if you have questions. (synthetic test data {i})"),
        })
    return out


def main():
    chunks, evals = build_dataset()
    with open(HERE / "faq_dataset.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(HERE / "eval_queries.jsonl", "w", encoding="utf-8") as f:
        for e in evals:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"Knowledge-base chunks: {len(chunks)} → data/faq_dataset.jsonl")
    print(f"Eval queries:          {len(evals)} → data/eval_queries.jsonl")


if __name__ == "__main__":
    main()
