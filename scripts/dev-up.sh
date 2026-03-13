#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'EOF'
Usage:
  scripts/dev-up.sh [--minimal|--full] [-d|--detach] [--automation] [--open]

Starts Geek Movie Forge local stack via Docker Compose.

Defaults:
  --minimal (starts web + api + their dependencies)

Options:
  --minimal       Start only web + api (and deps like postgres/redis).
  --full          Start all services in docker-compose.yml (workers, orchestrator, minio, remotion, etc).
  --automation    Also enable the "automation" profile (n8n).
  -d, --detach    Run containers in the background.
  --open          Open http://localhost:3000 after starting (best effort).
  -h, --help      Show this help.
EOF
}

stack="minimal"
detach=""
automation=false
open_browser=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --minimal) stack="minimal" ;;
    --full) stack="full" ;;
    --automation) automation=true ;;
    -d|--detach) detach="-d" ;;
    --open) open_browser=true ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
  shift
done

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker not found. Install Docker Engine / Docker Desktop first." >&2
  exit 1
fi

compose_cmd=()
if docker compose version >/dev/null 2>&1; then
  compose_cmd=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  echo "Error: docker compose not available. Install a recent Docker or docker-compose." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker daemon is not running. Start Docker and retry." >&2
  exit 1
fi

if [[ ! -f ".env" ]]; then
  if [[ ! -f ".env.example" ]]; then
    echo "Error: .env is missing and .env.example was not found." >&2
    exit 1
  fi
  cp .env.example .env
  echo "Created .env from .env.example"
fi

jwt_secret_line="$(grep -E '^JWT_SECRET=' .env | tail -n 1 || true)"
if [[ -z "$jwt_secret_line" ]]; then
  echo "Error: JWT_SECRET is missing in .env (required, min 32 chars)." >&2
  exit 1
fi
jwt_secret="${jwt_secret_line#JWT_SECRET=}"
jwt_secret="${jwt_secret%\"}"
jwt_secret="${jwt_secret#\"}"
if [[ ${#jwt_secret} -lt 32 ]]; then
  echo "Error: JWT_SECRET in .env must be at least 32 characters (current: ${#jwt_secret})." >&2
  echo "Edit .env and set a stronger JWT_SECRET, then retry." >&2
  exit 1
fi

profile_args=()
if [[ "$automation" == "true" ]]; then
  profile_args=(--profile automation)
fi

services=()
if [[ "$stack" == "minimal" ]]; then
  services=(api web)
fi

echo "Starting stack: ${stack}"
echo "Compose: ${compose_cmd[*]}"

set -x
"${compose_cmd[@]}" "${profile_args[@]}" up --build ${detach:+$detach} "${services[@]}"
set +x

if [[ "$detach" == "-d" ]]; then
  echo ""
  echo "Frontend: http://localhost:3000"
  echo "API:      http://localhost:8000  (health: /healthz, docs: /docs)"
  echo ""
  echo "Logs:     ${compose_cmd[*]} logs -f --tail=200"
  echo "Stop:     scripts/dev-down.sh"
fi

if [[ "$open_browser" == "true" ]]; then
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:3000" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then
    open "http://localhost:3000" >/dev/null 2>&1 || true
  fi
fi

