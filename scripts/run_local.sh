#!/usr/bin/env bash
set -euo pipefail

# Launch all services locally for quick testing. Not for distributed demo.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b}"

export MIN_AGENTS="${MIN_AGENTS:-1}"
export MIN_COUNCIL_HOSTS="${MIN_COUNCIL_HOSTS:-1}"
export ALLOW_CHAIR_SAME_HOST="${ALLOW_CHAIR_SAME_HOST:-true}"

export COUNCIL_ENDPOINTS="http://localhost:8001,http://localhost:8002,http://localhost:8003"
export CHAIR_ENDPOINT="http://localhost:8004"

PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

export MODEL_ID=council-a
python -m uvicorn agent_service.app:app --host 0.0.0.0 --port 8001 --app-dir "$ROOT_DIR" &
PIDS+=("$!")

export MODEL_ID=council-b
python -m uvicorn agent_service.app:app --host 0.0.0.0 --port 8002 --app-dir "$ROOT_DIR" &
PIDS+=("$!")

export MODEL_ID=council-c
python -m uvicorn agent_service.app:app --host 0.0.0.0 --port 8003 --app-dir "$ROOT_DIR" &
PIDS+=("$!")

export MODEL_ID=chairman
python -m uvicorn chairman_service.app:app --host 0.0.0.0 --port 8004 --app-dir "$ROOT_DIR" &
PIDS+=("$!")

python -m uvicorn orchestrator.app:app --host 0.0.0.0 --port 8000 --app-dir "$ROOT_DIR" &
PIDS+=("$!")

echo "Orchestrator running at http://localhost:8000/"
echo "Press Ctrl+C to stop all services."
wait
