#!/usr/bin/env bash
# Standing — one command to boot both dev servers.
#
# Starts the FastAPI backend (uvicorn, using backend/.venv if present) and
# the Vite frontend dev server together, waits for both, and tears both down
# on exit (Ctrl-C, or any early failure).
#
# DEMO_MODE defaults to 1: the whole product runs fully offline, no real API
# keys required (every external client falls back to canned fixtures in
# backend/fixtures/). Flip DEMO_MODE=0 (and fill in backend/.env) to hit the
# live Qwen/Exa/Firecrawl APIs.
#
# Usage:
#   ./dev.sh
#   DEMO_MODE=0 ./dev.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

# Only force a default here if the caller didn't set DEMO_MODE AND
# backend/.env doesn't set it either — otherwise we'd export DEMO_MODE=1
# into the child process env, and load_dotenv() never overrides an
# already-set env var, silently shadowing backend/.env's value.
if [ -z "${DEMO_MODE+x}" ]; then
    if [ -f "$BACKEND_DIR/.env" ] && grep -q '^DEMO_MODE=' "$BACKEND_DIR/.env"; then
        DEMO_MODE="$(grep '^DEMO_MODE=' "$BACKEND_DIR/.env" | tail -1 | cut -d= -f2-)"
    else
        DEMO_MODE=1
    fi
fi
export DEMO_MODE

# Prefer the project virtualenv if it exists, otherwise fall back to
# whatever `python`/`uvicorn` is on PATH.
if [ -x "$BACKEND_DIR/.venv/bin/uvicorn" ]; then
    UVICORN_BIN="$BACKEND_DIR/.venv/bin/uvicorn"
elif command -v uvicorn >/dev/null 2>&1; then
    UVICORN_BIN="$(command -v uvicorn)"
else
    echo "error: uvicorn not found. Run: python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt" >&2
    exit 1
fi

# Call the vite binary directly (not `npm run dev`). `npm run dev` forks an
# intermediate `sh -c vite` wrapper whose grandchild vite/node process is
# NOT reliably reaped when we kill just the npm PID on exit — it can be
# left running (holding the port) after this script exits. Execing the
# binary directly means FRONTEND_PID *is* the vite process.
if [ -x "$FRONTEND_DIR/node_modules/.bin/vite" ]; then
    VITE_BIN="$FRONTEND_DIR/node_modules/.bin/vite"
elif command -v vite >/dev/null 2>&1; then
    VITE_BIN="$(command -v vite)"
else
    echo "error: vite not found. Run: cd frontend && npm install" >&2
    exit 1
fi

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "Shutting down..."
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
        wait "$FRONTEND_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

echo "Starting Standing (DEMO_MODE=$DEMO_MODE)..."
echo ""

(
    cd "$BACKEND_DIR"
    exec "$UVICORN_BIN" app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

(
    cd "$FRONTEND_DIR"
    exec "$VITE_BIN" --port "$FRONTEND_PORT" --strictPort
) &
FRONTEND_PID=$!

sleep 1
echo ""
echo "============================================================"
echo " Backend:  http://$BACKEND_HOST:$BACKEND_PORT   (docs at /docs, health at /api/health)"
echo " Frontend: http://localhost:$FRONTEND_PORT"
echo "============================================================"
echo ""
echo "Press Ctrl-C to stop both servers."

wait "$BACKEND_PID" "$FRONTEND_PID"
