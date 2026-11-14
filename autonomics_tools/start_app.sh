#!/usr/bin/env bash

set -u
set -o pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

if ! cd "$PROJECT_ROOT"; then
    printf '[FAIL] Could not enter project directory: %s\n' "$PROJECT_ROOT" >&2
    exit 1
fi

if [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON_BIN=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    printf '[FAIL] Python was not found. Activate an environment with Python installed.\n' >&2
    exit 1
fi

PORT="${STREAMLIT_PORT:-8501}"
HOST="${STREAMLIT_HOST:-127.0.0.1}"

case "$PORT" in
    ''|*[!0-9]*)
        printf '[FAIL] STREAMLIT_PORT must be a number from 1 to 65535.\n' >&2
        exit 1
        ;;
esac

if ! "$PYTHON_BIN" -c 'import sys; port = int(sys.argv[1]); sys.exit(0 if 1 <= port <= 65535 else 1)' "$PORT" >/dev/null 2>&1; then
    printf '[FAIL] STREAMLIT_PORT must be a number from 1 to 65535.\n' >&2
    exit 1
fi

HEALTH_URL="http://${HOST}:${PORT}/_stcore/health"
if "$PYTHON_BIN" -c 'import sys, urllib.request; response = urllib.request.urlopen(sys.argv[1], timeout=2); sys.exit(0 if 200 <= response.status < 300 else 1)' "$HEALTH_URL" >/dev/null 2>&1; then
    printf '[PASS] Streamlit is already healthy at %s; not starting a duplicate.\n' "$HEALTH_URL"
    exit 0
fi

if "$PYTHON_BIN" -c 'import socket, sys; connection = socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=1); connection.close()' "$HOST" "$PORT" >/dev/null 2>&1; then
    printf '[FAIL] Port %s is already occupied but is not a healthy Streamlit app.\n' "$PORT" >&2
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import streamlit, redbus_automation' >/dev/null 2>&1; then
    printf '[FAIL] Streamlit or redbus_automation cannot be imported with %s.\n' "$PYTHON_BIN" >&2
    exit 1
fi

printf '[PASS] Python, Streamlit, and redbus_automation are available.\n'
printf '[INFO] Starting the existing app at http://%s:%s (Ctrl+C to stop).\n' "$HOST" "$PORT"
exec "$PYTHON_BIN" -m streamlit run app.py --server.address "$HOST" --server.port "$PORT" --server.headless true
