#!/usr/bin/env bash
# ==============================================================================
# Start Script for RedBus Intelligent Autonomics Platform
# Compatible with: Windows 11 Git Bash and Linux Bash
# Usage: bash scripts/start.sh
# ==============================================================================

set -eo pipefail

echo "=================================================================="
echo " Launching RedBus Intelligent Automation Dashboard"
echo "=================================================================="

# 1. Prefer the project virtual environment directly so Git Bash does not fall back to Windows App Execution aliases.
if [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON_BIN=".venv/Scripts/python.exe"
    echo "[✓] Using project virtual environment (Windows)."
elif [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
    echo "[✓] Using project virtual environment (POSIX)."
else
    if [ -f ".venv/Scripts/activate" ]; then
        # shellcheck disable=SC1091
        source ".venv/Scripts/activate"
        echo "[✓] Virtual environment activated (Windows)."
    elif [ -f ".venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        source ".venv/bin/activate"
        echo "[✓] Virtual environment activated (POSIX)."
    fi

    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_BIN="python"
    else
        echo "ERROR: Python is not available in the current environment." >&2
        exit 1
    fi
fi

# 2. Verify Streamlit and Core Package Imports
if ! "$PYTHON_BIN" -c "import streamlit, redbus_automation" >/dev/null 2>&1; then
    echo "ERROR: Required packages (streamlit, redbus_automation) cannot be imported." >&2
    echo "Please run 'bash scripts/setup.sh' first to configure dependencies." >&2
    exit 1
fi

# 3. Launch Streamlit Application
PORT=${STREAMLIT_PORT:-8501}
echo "[✓] Starting Streamlit server on port $PORT..."
echo "[*] Access the dashboard at: http://localhost:$PORT"
echo "[*] Press Ctrl+C to terminate the dashboard."
echo "------------------------------------------------------------------"

exec "$PYTHON_BIN" -m streamlit run app.py --server.port "$PORT" --server.headless true
