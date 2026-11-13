#!/usr/bin/env bash
# ==============================================================================
# Start Script for Streamlit Dashboard
# Compatible with: Windows 11 Git Bash and Linux Bash
# ==============================================================================

set -eo pipefail

echo "=================================================================="
echo " Launching RedBus Intelligent Automation Dashboard"
echo "=================================================================="

# 1. Activate Virtual Environment if available
if [ -f ".venv/Scripts/activate" ]; then
    # shellcheck disable=SC1091
    source ".venv/Scripts/activate"
    echo "[✓] Virtual environment activated (Windows)."
elif [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
    echo "[✓] Virtual environment activated (POSIX)."
fi

# 2. Verify Python Availability
if ! command -v python >/dev/null 2>&1; then
    echo "ERROR: Python is not available in the current environment." >&2
    exit 1
fi

# 3. Verify Streamlit and Core Package Imports
if ! python -c "import streamlit, redbus_automation" >/dev/null 2>&1; then
    echo "ERROR: Required packages (streamlit, redbus_automation) cannot be imported." >&2
    echo "Please run 'bash scripts/setup.sh' first to configure dependencies." >&2
    exit 1
fi

# 4. Launch Streamlit Application
PORT=${STREAMLIT_PORT:-8501}
echo "[✓] Starting Streamlit server on port $PORT..."
echo "[*] Access the dashboard at: http://localhost:$PORT"
echo "[*] Press Ctrl+C to terminate the dashboard."
echo "------------------------------------------------------------------"

exec python -m streamlit run app.py --server.port "$PORT" --server.headless true
