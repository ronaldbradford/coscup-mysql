# 環境建置指南（GCP / Azure VM + Docker Compose）

目標：在雲端 VM 上架好完整 demo 環境（MySQL 9.7、pgvector、Ollama），
會前完成資料 ingest 與 benchmark，現場只跑「查詢與問答」。

## 1. VM 規格建議

| 項目 | GCP | Azure | 說明 |
| --- | --- | --- | --- |
| 機型 | `e2-standard-4`（4 vCPU / 16GB） | `Standard_D4s_v5` | Ollama 跑 bge-m3 + qwen3:4b 需要 ~8GB，兩座 DB + 10 萬向量再抓 4GB |
| 磁碟 | 60GB SSD（pd-balanced） | 64GB Premium SSD | image + 模型 + 10 萬筆雙庫資料約 25GB，留餘裕 |
| OS | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS | |
| 區域 | `asia-east1`（彰化） | `East Asia`（香港） | 離會場近，SSH 延遲低 |
| 費用參考 | 約 US$0.15/hr | 約 US$0.19/hr | 只在準備與演講期間開機即可 |

GCP 建立指令（gcloud）：

```bash
gcloud compute instances create coscup-rag \
  --machine-type=e2-standard-4 --zone=asia-east1-b \
  --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
  --boot-disk-size=60GB --boot-disk-type=pd-balanced
gcloud compute ssh coscup-rag --zone=asia-east1-b
```

> 防火牆不需要開任何對外 port——一切透過 SSH 操作，資料庫只聽 localhost（docker 預設 bind 0.0.0.0，VM 對外防火牆保持只開 22 即可）。

## 2. 安裝 Docker 與工具

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl git make python3-pip python3-venv
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
docker --version && docker compose version
```

## 3. 部署 demo

```bash
git clone <你的 repo URL> coscup && cd coscup
python3 -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt

make up          # MySQL 9.7 + pgvector（首次拉 image 約 2 分鐘）
make up-ai       # Ollama + 拉 bge-m3（~1.2GB）與 qwen3:4b（~2.6GB），約 5-10 分鐘
make dataset     # 產生知識庫（43 chunks + 173 評估問句）
make ingest      # 真實 embedding + 寫入兩座 DB（bge-m3，約 1-2 分鐘）
```

驗收：

```bash
cd app
python3 search_mysql.py "退款多久會到？"     # 應命中 return-004
python3 search_pg.py    "退款多久會到？"     # 結果應與上行一致
python3 chatbot.py -q "刷卡一直失敗怎麼辦"    # 完整 RAG 回答（首次載入模型較慢）
```

## 4. 會前一天：跑 benchmark（重要）

benchmark 要在**你的 VM** 上重跑一次，把簡報表格換成自己的數字：

```bash
make bench-10k    # 約 3 分鐘
make bench-100k   # 約 15-20 分鐘（含 10 萬筆 embedding 與雙庫寫入）
cat bench/results-*.csv
```

> 注意：bench 會在庫裡留下 10 萬筆 filler。跑完 benchmark 後，若要讓 demo I
> 回到「小而美」狀態，重新 `make ingest` 即可（會 TRUNCATE 後重灌 43 筆）。
> 建議順序：先錄備援影片 → 跑 benchmark 抄數字 → `make ingest` 還原 → 驗收一次。

## 5. 現場連線與呈現

- 用 `tmux` 開好三個窗格：`chatbot`、`mysql-cli`、`psql-cli`，斷線也不丟狀態：
  ```bash
  tmux new -s demo
  # 窗格 0: cd app && source ../.venv/bin/activate
  # 窗格 1: make mysql-cli
  # 窗格 2: make psql-cli
  ```
- 終端機字體調到 20pt 以上，深色背景亮色字；`PS1` 縮短提示字元。
- SSH 斷線重連腳本先寫好：`gcloud compute ssh coscup-rag --zone=asia-east1-b -- -t tmux attach -t demo`

## 6. 本機備援（雙保險）

會場網路不可信。筆電上準備一份完全相同的環境：

```bash
# 筆電（16GB RAM 可跑；Ollama 改用量化較小的 qwen3:1.7b 亦可）
make up && make up-ai && make dataset && make ingest
```

加上預錄影片（見 runbook），形成三層防線：雲端 VM → 本機 compose → 影片。

## 7. 版本紀錄（會前最後一週再確認一次）

| 元件 | 本文撰寫時版本 | 確認方式 |
| --- | --- | --- |
| MySQL | 9.7.2（社群版，仍無 DISTANCE/ANN） | `docker exec rag-mysql mysql -V`；release notes |
| PostgreSQL | 18.4 | `SELECT version();` |
| pgvector | 0.8.6 | `SELECT extversion FROM pg_extension WHERE extname='vector';` |
| Ollama / bge-m3 / qwen3:4b | latest | `ollama list` |
| MyVector（選配） | v1.26.5 | github.com/askdba/myvector releases |

若 8 月前 MySQL 釋出新版把 vector search 下放社群版——那是大新聞，投影片第 10-12 頁要改寫，benchmark 全部重跑（這也會讓演講更精彩，不是壞事）。
