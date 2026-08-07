#!/usr/bin/env python3
"""產生「綠豆選物 LitoShop」合成客服知識庫。

輸出兩個檔案：
  data/faq_dataset.jsonl  — RAG 知識庫（每行一個 chunk：id, category, title, content）
  data/eval_queries.jsonl — 評估用問句（query, expected_id），用來 demo / 驗證檢索品質

另提供 make_filler(n) 供 benchmark 擴增至 N 筆合成資料。

授權：CC0-1.0（合成資料，無真實個資）
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).parent

# 問句改寫模板：同一個知識點，客人會用很多種問法 —— 這正是 RAG 要解的問題
PREFIXES = ["", "請問", "你好，", "不好意思，", "想問一下", "急！", "哈囉，請問"]
SUFFIXES = ["", "謝謝", "麻煩了", "拜託幫我看看", "在線等"]

REPHRASE = {
    "order-001": ["我的訂單現在到哪了", "怎麼看訂單處理到哪個階段", "訂單進度查詢"],
    "order-002": ["我按錯了想取消訂單", "剛下單就後悔了能退嗎", "訂單還沒出貨可以取消嗎"],
    "order-003": ["地址填錯了怎麼改", "收件人資料可以更新嗎", "想換超商門市取貨"],
    "order-004": ["等好幾天了都沒出貨", "出貨要多久", "怎麼還不出貨"],
    "order-005": ["訂單莫名其妙被取消", "沒去領貨訂單會怎樣", "我的訂單自己不見了"],
    "order-006": ["兩筆訂單可以一起寄嗎", "合併運送可以嗎", "怎麼省運費"],
    "ship-001": ["運費多少錢", "滿多少免運", "有超商取貨嗎", "寄到澎湖要多久"],
    "ship-002": ["包裹查詢", "怎麼知道貨到哪了", "物流單號在哪看"],
    "ship-003": ["超商的貨幾天內要拿", "沒去取貨會被罰嗎", "包裹被退回了怎麼辦"],
    "ship-004": ["宅配可以約時間嗎", "可以晚上送貨嗎", "白天不在家怎麼收貨"],
    "ship-005": ["可以寄到香港嗎", "有寄國外嗎", "人在海外怎麼買"],
    "ship-006": ["顯示已簽收但沒拿到貨", "包裹不見了", "貨被別人領走了怎麼辦"],
    "return-001": ["要怎麼退貨", "七天鑑賞期是什麼", "退貨流程"],
    "return-002": ["內衣可以退嗎", "食品拆封了還能退嗎", "什麼東西不能退"],
    "return-003": ["收到的東西是壞的", "商品有瑕疵想換新的", "寄來就破了怎麼辦"],
    "return-004": ["退款什麼時候會到", "錢多久退回來", "刷卡退款會退到哪"],
    "return-005": ["尺寸不合想換一件", "買錯顏色可以換嗎", "換貨要運費嗎"],
    "return-006": ["退貨發票怎麼處理", "有打統編的發票退貨", "發票要寄回去嗎"],
    "pay-001": ["可以用 LINE Pay 嗎", "有貨到付款嗎", "付款方式有哪些"],
    "pay-002": ["刷卡一直失敗", "信用卡過不了", "付款被拒絕是為什麼"],
    "pay-003": ["轉帳帳號在哪裡", "ATM 帳號多久有效", "匯款後多久會確認"],
    "pay-004": ["可以分期嗎", "分期有手續費嗎", "分 12 期要利息嗎"],
    "pay-005": ["扣款了但訂單沒成立", "付了錢還顯示待付款", "被重複扣款怎麼辦"],
    "pay-006": ["想改用刷卡付款", "付款方式可以換嗎", "選錯付款方式了"],
    "invoice-001": ["發票怎麼開", "發票會寄給我嗎", "可以存手機條碼嗎"],
    "invoice-002": ["發票要打統編", "忘記打統編了怎麼辦", "發票可以改公司戶嗎"],
    "invoice-003": ["發票中獎怎麼領", "中獎會通知我嗎", "雲端發票中獎領獎"],
    "member-001": ["怎麼註冊", "可以用 LINE 登入嗎", "新會員有優惠嗎"],
    "member-002": ["會員等級差在哪", "怎麼升金卡", "黑卡有什麼好處"],
    "member-003": ["購物金怎麼用", "購物金會過期嗎", "購物金可以折多少"],
    "member-004": ["密碼忘記了", "登入不了怎麼辦", "重設密碼沒收到信"],
    "member-005": ["我想刪除帳號", "怎麼註銷會員", "刪帳號後資料會留著嗎"],
    "promo-001": ["優惠券在哪領", "折價券怎麼用", "優惠券可以疊加嗎"],
    "promo-002": ["折扣碼不能用", "輸入折扣碼沒反應", "折扣碼顯示已失效"],
    "promo-003": ["剛買完就降價", "可以退差價嗎", "買貴退差價"],
    "product-001": ["什麼時候補貨", "缺貨還會進嗎", "有貨可以通知我嗎"],
    "product-002": ["尺寸怎麼選", "尺寸表在哪", "我 170 該穿 M 還是 L"],
    "product-003": ["實品會有色差嗎", "照片跟實物一樣嗎", "顏色不喜歡能退嗎"],
    "account-001": ["接到自稱客服的電話", "有簡訊叫我解除分期", "這是詐騙嗎"],
    "account-002": ["帳號被盜了", "有奇怪的登入紀錄", "出現不是我下的訂單"],
    "support-001": ["保固多久", "壞了怎麼送修", "維修要錢嗎"],
    "support-002": ["客服電話幾號", "怎麼找真人客服", "客服上班時間"],
    "support-003": ["我要客訴", "服務很差要投訴", "意見回饋管道"],
}

# benchmark 填充資料模板（模擬更大量、更雜的知識庫內容）
FILLER_TOPICS = ["訂單", "物流", "退換貨", "付款", "發票", "會員", "優惠", "商品", "帳號安全", "售後"]
FILLER_SUBJECTS = ["宅配", "超商取貨", "信用卡", "購物金", "優惠券", "電子發票", "保固維修",
                   "貨到通知", "分期付款", "會員等級", "退款", "換貨", "簡訊通知", "帳號驗證"]
FILLER_VERBS = ["查詢", "申請", "取消", "變更", "設定", "使用", "延長", "補發", "綁定", "解除"]


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
            "content": f"【{faq['category']}】{faq['question']}\n{faq['answer']}",
        })
        # 原問句 + 改寫問句 → 評估集
        for q in [faq["question"], *REPHRASE.get(faq["id"], [])]:
            evals.append({"query": q, "expected_id": faq["id"], "category": faq["category"]})
    return chunks, evals


def make_filler(n, seed_val=42):
    """產生 n 筆合成填充 chunk（僅供效能測試，內容為模板組合）。"""
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
            "title": f"{subj}{verb}相關說明 #{i}",
            "content": (f"【{topic}】關於{subj}的{verb}：作業時間約 {days} 個工作天，"
                        f"相關門檻為 {amount} 元。詳細規定請參閱條款第 {rng.randint(1,99)} 條，"
                        f"如有疑問請聯繫客服。（合成測試資料 {i}）"),
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
    print(f"知識庫 chunks: {len(chunks)} 筆 → data/faq_dataset.jsonl")
    print(f"評估問句:      {len(evals)} 筆 → data/eval_queries.jsonl")


if __name__ == "__main__":
    main()
