# Environment setup (GCP / Azure VM + Docker Compose)

Goal: stand up the full demo on a cloud VM (MySQL 9.7, pgvector, Ollama),
finish ingest and the benchmark before the event, and on stage only run queries and Q&A.

## 1. Suggested VM size

| Item | GCP | Azure | Notes |
| --- | --- | --- | --- |
| Machine | `e2-standard-4` (4 vCPU / 16 GB) | `Standard_D4s_v5` | Ollama needs ~8 GB for bge-m3 + qwen3:4b; the two DBs + 100k vectors need another ~4 GB |
| Disk | 60 GB SSD (pd-balanced) | 64 GB Premium SSD | images + models + 100k dual-DB data ≈ 25 GB; leave headroom |
| OS | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS | |
| Region | `asia-east1` (Changhua) | `East Asia` (Hong Kong) | close to the venue, low SSH latency |
| Cost (approx.) | ~US$0.15/hr | ~US$0.19/hr | only run it during prep and the talk |

GCP create command (`gcloud`):

```bash
gcloud compute instances create coscup-rag \
  --machine-type=e2-standard-4 --zone=asia-east1-b \
  --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
  --boot-disk-size=60GB --boot-disk-type=pd-balanced
gcloud compute ssh coscup-rag --zone=asia-east1-b
```

> Do not open extra inbound ports. Everything is over SSH. Databases listen on localhost
> (Docker binds 0.0.0.0 by default; keep the VM firewall at SSH/22 only).

## 2. Install Docker and tools

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl git make python3-pip python3-venv
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
docker --version && docker compose version
```

## 3. Deploy the demo

```bash
git clone <your repo URL> coscup && cd coscup
python3 -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt

make up          # MySQL 9.7 + pgvector (first image pull ~2 min)
make up-ai       # Ollama + pull bge-m3 (~1.2 GB) and qwen3:4b (~2.6 GB), about 5–10 min
                 # On Linux, best-effort dual-iptables fix (no sudo prompt; see §8)
make dataset     # generate the knowledge base (43 chunks + 173 eval queries)
make ingest      # real embeddings + write both DBs (bge-m3, about 1–2 min)
```

Acceptance:

```bash
cd app
python3 search_mysql.py "How long until my refund arrives?"     # should hit return-004
python3 search_pg.py    "How long until my refund arrives?"     # should match the line above
python3 chatbot.py -q "my card keeps failing, what should I do?"    # full RAG answer (first model load is slower)
```

## 4. The day before: run the benchmark (important)

Re-run the benchmark on **your** VM and replace the slide table with your numbers:

```bash
make bench-10k    # ~3 min
make bench-100k   # ~15–20 min (includes 100k embeddings and dual-DB writes)
cat bench/results-*.csv
```

> Note: bench leaves 100k filler rows in the databases. After the benchmark, restore Demo I
> to the “small and tidy” state with `make ingest` (TRUNCATE + reload the 43 rows).
> Suggested order: record backup videos → run bench and copy numbers → `make ingest` to restore → one acceptance pass.

## 5. On-site connection and presentation

- Open three tmux panes: `chatbot`, `mysql-cli`, `psql-cli`, so a disconnect does not lose state:
  ```bash
  tmux new -s demo
  # pane 0: cd app && source ../.venv/bin/activate
  # pane 1: make mysql-cli
  # pane 2: make psql-cli
  ```
- Terminal font 20pt or larger, dark background, light text; shorten `PS1`.
- Have the reconnect command ready: `gcloud compute ssh coscup-rag --zone=asia-east1-b -- -t tmux attach -t demo`

## 6. Laptop fallback (belt and suspenders)

Venue networks are untrustworthy. Keep an identical environment on the laptop:

```bash
# Laptop (16 GB RAM is enough; you can swap Ollama to the smaller qwen3:1.7b)
make up && make up-ai && make dataset && make ingest
```

Add the pre-recorded videos (see the runbook) for three layers: cloud VM → local compose → video.

## 7. Version log (re-check the week before the talk)

| Component | Version at writing | How to confirm |
| --- | --- | --- |
| MySQL | 9.7.2 (Community; still no DISTANCE/ANN) | `docker exec rag-mysql mysql -V`; release notes |
| PostgreSQL | 18.4 | `SELECT version();` |
| pgvector | 0.8.6 | `SELECT extversion FROM pg_extension WHERE extname='vector';` |
| Ollama / bge-m3 / qwen3:4b | latest | `ollama list` |
| MyVector (optional) | v1.26.5 | github.com/askdba/myvector releases |

If MySQL ships Community vector search before August — that is big news. Rewrite slides 10–12 and re-run every benchmark (it also makes the talk better, not worse).

## 8. Troubleshooting: `ollama pull` i/o timeout (dual iptables)

Symptom: the **host** can reach `https://registry.ollama.ai`, but inside a compose container the pull hangs and fails with:

```text
docker exec rag-ollama ollama pull bge-m3
Error: dial tcp 104.18.x.x:443: i/o timeout
```

This is not DNS, not a Cloudflare block, not an HTTP proxy, and not IPv6-first. On Debian/Ubuntu **nested-Docker** (and some cloud VMs) Docker writes FORWARD ACCEPTs with **iptables-nft** for the compose bridge (`br-*` / `coscup-mysql_default`), while leftover **iptables-legacy** still has `FORWARD` policy `DROP` and only allows `docker0`. The kernel evaluates both; the legacy DROP wins, so all HTTPS from compose containers times out.

Docker Desktop on macOS/Windows is not affected.

Fix (idempotent; needs root / sudo):

```bash
make fix-docker-net
# or: sudo ./scripts/fix-docker-bridge-forward.sh
```

Then retry `docker exec rag-ollama ollama pull bge-m3`. `make up-ai` already runs the script with `--best-effort` (Linux + `iptables-legacy` only, never prompts for a password). If you are not root and sudo is not passwordless, run `make fix-docker-net` once by hand.
