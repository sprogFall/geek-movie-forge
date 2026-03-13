#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'EOF'
Usage:
  scripts/dev-down.sh [--volumes]

Stops Geek Movie Forge local stack via Docker Compose.

Options:
  --volumes   Also remove named volumes (postgres/redis/minio data).
  -h, --help  Show this help.
EOF
}

remove_volumes=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --volumes) remove_volumes=true ;;
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
  echo "Error: docker not found." >&2
  exit 1
fi

compose_cmd=()
if docker compose version >/dev/null 2>&1; then
  compose_cmd=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  echo "Error: docker compose not available." >&2
  exit 1
fi

down_args=(down)
if [[ "$remove_volumes" == "true" ]]; then
  down_args+=(--volumes)
fi

set -x
"${compose_cmd[@]}" "${down_args[@]}"
set +x

