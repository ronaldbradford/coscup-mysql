#!/usr/bin/env bash
# Fix dual iptables: nft accepts compose-bridge egress, but leftover
# iptables-legacy FORWARD (policy DROP) still drops those packets.
#
# Symptom (verified on Debian nested-Docker):
#   Host can reach https://registry.ollama.ai.
#   Inside compose containers on the project bridge (br-*), all HTTPS
#   times out, e.g.:
#     docker exec rag-ollama ollama pull bge-m3
#     Error: dial tcp 104.18.x.x:443: i/o timeout
#   Not DNS, not a Cloudflare block, not HTTP proxy, not IPv6-first.
#
# Cause:
#   Docker writes its rules with iptables-nft (DOCKER-FORWARD ACCEPTs the
#   compose br-* bridge). A leftover iptables-legacy filter table still has
#   FORWARD policy DROP and only ACCEPTs docker0. The kernel evaluates both
#   tables; the legacy DROP wins.
#
# Fix:
#   Add the same ACCEPT pair for the compose bridge in iptables-legacy.
#   Equivalent to the proven rules:
#     iptables-legacy -I DOCKER-FORWARD 4 -i br-<id12> -j ACCEPT
#     iptables-legacy -I DOCKER-FORWARD 5 -o br-<id12> \
#       -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
#   This script appends those rules when missing (position-independent;
#   ACCEPT anywhere in the chain is enough). Safe to re-run.
#
# Usage:
#   sudo ./scripts/fix-docker-bridge-forward.sh
#   ./scripts/fix-docker-bridge-forward.sh [network-name ...]
#   ./scripts/fix-docker-bridge-forward.sh --best-effort
#
# --best-effort (used by `make up-ai`): Linux + iptables-legacy only;
# never prompts for a sudo password; no-ops on macOS / Docker Desktop.
# Requires root (or passwordless sudo) to change rules.
#
# Environment:
#   COMPOSE_PROJECT_NAME   used if no network name is given
#   DOCKER_COMPOSE_NETWORK explicit compose network name (overrides discovery)
#   IPTABLES_LEGACY        iptables-legacy binary (default: iptables-legacy)
#   SYSFS_NET              net sysfs dir (default: /sys/class/net)

set -euo pipefail

BEST_EFFORT=0
SHOW_HELP=0
NETWORK_ARGS=()
SYSFS_NET=${SYSFS_NET:-/sys/class/net}
IPTABLES_LEGACY=${IPTABLES_LEGACY:-iptables-legacy}

usage() {
  cat <<'EOF'
Usage: fix-docker-bridge-forward.sh [--best-effort] [compose-network ...]

Idempotent fix for dual iptables (nft vs legacy) dropping Docker compose
bridge egress. Typical symptom: `ollama pull` fails with
`dial tcp …:443: i/o timeout` from a compose container while the host
can reach the same URL.

  --best-effort   no-op unless Linux + iptables-legacy; never prompt for sudo
  -h, --help      show this help

Not applicable (exit 0) on macOS / Docker Desktop and when iptables-legacy
is absent. Needs root or sudo only to insert the missing ACCEPT rules.

Examples:
  make fix-docker-net
  sudo ./scripts/fix-docker-bridge-forward.sh
  sudo ./scripts/fix-docker-bridge-forward.sh coscup-mysql_default
EOF
}

for arg in "$@"; do
  case "$arg" in
    --best-effort) BEST_EFFORT=1 ;;
    -h|--help) SHOW_HELP=1 ;;
    -*)
      echo "Unknown option: $arg" >&2
      usage >&2
      exit 2
      ;;
    *) NETWORK_ARGS+=("$arg") ;;
  esac
done

if [[ $SHOW_HELP -eq 1 ]]; then
  usage
  exit 0
fi

log() { printf '%s\n' "$*"; }
warn() { printf '%s\n' "$*" >&2; }

# Host does not have this failure mode (always 0 so `make fix-docker-net`
# is safe on macOS / nft-only Docker Desktop). Silent under --best-effort
# so `make up-ai` stays quiet on Docker Desktop.
skip() {
  if [[ $BEST_EFFORT -eq 0 ]]; then
    warn "$1"
  fi
  exit 0
}

die() {
  warn "$1"
  if [[ $BEST_EFFORT -eq 1 ]]; then
    exit 0
  fi
  exit 1
}

OS=$(uname -s)
if [[ $OS != Linux ]]; then
  skip "Skipping dual-iptables fix on $OS (Linux nested-Docker only; Docker Desktop is unaffected)."
fi

if ! command -v "$IPTABLES_LEGACY" >/dev/null 2>&1; then
  skip "Skipping dual-iptables fix: iptables-legacy not found (nft-only / Docker Desktop)."
fi

if ! command -v docker >/dev/null 2>&1; then
  die "docker is not installed or not on PATH."
fi

IPT_BIN=("$IPTABLES_LEGACY")
if [[ ${EUID} -ne 0 ]] && ! "$IPTABLES_LEGACY" -L FORWARD -n >/dev/null 2>&1; then
  if ! command -v sudo >/dev/null 2>&1; then
    die "Must run as root (or with sudo) to change iptables-legacy rules."
  fi
  if [[ $BEST_EFFORT -eq 1 ]]; then
    if ! sudo -n true >/dev/null 2>&1; then
      warn "Compose-bridge HTTPS may time out (dual iptables nft/legacy)."
      warn "If \`ollama pull\` fails with 'dial tcp …:443: i/o timeout', run: make fix-docker-net"
      exit 0
    fi
    IPT_BIN=(sudo -n "$IPTABLES_LEGACY")
  else
    IPT_BIN=(sudo "$IPTABLES_LEGACY")
  fi
fi

run_ipt() { "${IPT_BIN[@]}" "$@"; }

if ! run_ipt -L FORWARD -n >/dev/null 2>&1; then
  die "Cannot list iptables-legacy FORWARD (need root / sudo)."
fi

FORWARD_POLICY=$(run_ipt -S FORWARD 2>/dev/null | awk '/^-P FORWARD/{print $3; exit}')
if [[ $BEST_EFFORT -eq 1 && ${FORWARD_POLICY:-ACCEPT} != DROP ]]; then
  # Not the leftover-legacy-DROP failure mode; leave the host alone.
  exit 0
fi

chain_exists() {
  run_ipt -L "$1" -n >/dev/null 2>&1
}

TARGET_CHAIN=DOCKER-FORWARD
if ! chain_exists DOCKER-FORWARD; then
  TARGET_CHAIN=FORWARD
fi

# Resolve compose network IDs → br-<first 12 of Id>
network_ids=()

add_network_id() {
  local name=$1 id
  id=$(docker network inspect "$name" -f '{{.Id}}' 2>/dev/null || true)
  if [[ -z $id ]]; then
    return 1
  fi
  network_ids+=("$id")
  return 0
}

if [[ ${#NETWORK_ARGS[@]} -gt 0 ]]; then
  for name in "${NETWORK_ARGS[@]}"; do
    if ! add_network_id "$name"; then
      die "Docker network '$name' not found. Start compose first (make up / make up-ai)."
    fi
  done
elif [[ -n ${DOCKER_COMPOSE_NETWORK:-} ]]; then
  if ! add_network_id "$DOCKER_COMPOSE_NETWORK"; then
    die "Docker network '$DOCKER_COMPOSE_NETWORK' not found."
  fi
else
  # Prefer compose-labeled networks, then ${project}_default.
  while IFS= read -r id; do
    [[ -n $id ]] && network_ids+=("$id")
  done < <(docker network ls --filter label=com.docker.compose.network --format '{{.ID}}' 2>/dev/null || true)

  if [[ ${#network_ids[@]} -eq 0 ]]; then
    project=${COMPOSE_PROJECT_NAME:-}
    if [[ -z $project ]]; then
      project=$(docker compose config 2>/dev/null | awk '/^name:/{print $2; exit}' || true)
    fi
    if [[ -z $project ]]; then
      project=$(basename "$(pwd)")
    fi
    add_network_id "${project}_default" || true
  fi
fi

if [[ ${#network_ids[@]} -eq 0 ]]; then
  die "No compose bridge found. Start services first: docker compose up -d"
fi

added=0
found_bridge=0

declare -A seen_br=()
for id in "${network_ids[@]}"; do
  br="br-${id:0:12}"
  [[ -n ${seen_br[$br]+x} ]] && continue
  seen_br[$br]=1

  if [[ ! -d $SYSFS_NET/$br ]]; then
    continue
  fi
  found_bridge=1

  if ! run_ipt -C "$TARGET_CHAIN" -i "$br" -j ACCEPT 2>/dev/null; then
    # Proven fix used -I DOCKER-FORWARD 4/5; append is equivalent for ACCEPT
    # and does not depend on how many docker0 rules already exist.
    run_ipt -A "$TARGET_CHAIN" -i "$br" -j ACCEPT
    log "Added ACCEPT -i $br  ($TARGET_CHAIN)"
    added=1
  else
    log "Already present: ACCEPT -i $br  ($TARGET_CHAIN)"
  fi

  if ! run_ipt -C "$TARGET_CHAIN" -o "$br" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null; then
    run_ipt -A "$TARGET_CHAIN" -o "$br" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
    log "Added ACCEPT RELATED,ESTABLISHED -o $br  ($TARGET_CHAIN)"
    added=1
  else
    log "Already present: ACCEPT RELATED,ESTABLISHED -o $br  ($TARGET_CHAIN)"
  fi
done

if [[ $found_bridge -eq 0 ]]; then
  die "Compose network IDs found, but no br-* interface under $SYSFS_NET."
fi

if [[ $added -eq 1 || $BEST_EFFORT -eq 0 ]]; then
  log "iptables-legacy $TARGET_CHAIN (FORWARD policy ${FORWARD_POLICY:-unknown}):"
  run_ipt -L "$TARGET_CHAIN" -n -v | head -20 || true
fi
