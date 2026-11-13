#!/usr/bin/env bash
# ==============================================================================
# Setup Script for RedBus Intelligent Ticket Search and Automation System
# Compatible with: Windows 11 Git Bash and Linux Bash
# ==============================================================================

set -eo pipefail

echo "=================================================================="
echo " Starting RedBus Automation Environment Setup"
echo "=================================================================="

# 1. Detect Python Command
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "ERROR: Neither 'python3' nor 'python' was found in your PATH." >&2
    echo "Please install Python 3.9+ and ensure it is added to your PATH." >&2
    exit 1
fi

PY_VERSION=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[✓] Detected Python: $PYTHON_BIN (Version: $PY_VERSION)"

# 2. Create Virtual Environment if missing
if [ ! -d ".venv" ]; then
    echo "[*] Creating virtual environment (.venv)..."
    $PYTHON_BIN -m venv .venv
    echo "[✓] Virtual environment created successfully."
else
    echo "[✓] Existing virtual environment (.venv) detected."
fi

# 3. Activate Virtual Environment
if [ -f ".venv/Scripts/activate" ]; then
    # Windows Git Bash
    # shellcheck disable=SC1091
    source .venv/Scripts/activate
    echo "[✓] Activated Windows virtual environment (.venv/Scripts/activate)."
elif [ -f ".venv/bin/activate" ]; then
    # Linux / macOS Bash
    # shellcheck disable=SC1091
    source .venv/bin/activate
    echo "[✓] Activated POSIX virtual environment (.venv/bin/activate)."
else
    echo "WARNING: Could not locate activation script. Proceeding with system Python."
fi

# 4. Create Required Runtime Directories
echo "[*] Ensuring required runtime directories exist..."
mkdir -p data logs reports tests scripts docs .github/workflows
echo "[✓] Directory tree verified."

# 5. Upgrade pip and Install Dependencies
echo "[*] Installing project dependencies from requirements.txt..."
python -m pip install --upgrade pip --quiet || true
python -m pip install -r requirements.txt

# 6. Verify Critical Package Installations
echo "[*] Verifying critical installations..."
python -c "import streamlit, pytest; print(f'[✓] Streamlit {streamlit.__version__} and Pytest {pytest.__version__} verified successfully.')"

echo "=================================================================="
echo " Setup Completed Successfully!"
echo " Next steps:"
echo "   - Run tests     : bash scripts/run_tests.sh"
echo "   - Health check  : bash scripts/health_check.sh"
echo "   - Start web app : bash scripts/start_app.sh"
echo "   - Run CLI tool  : python -m redbus_automation.main"
echo "=================================================================="
exit 0
