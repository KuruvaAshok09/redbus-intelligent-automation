#!/usr/bin/env bash
# ==============================================================================
# Automated Test Runner Script
# Compatible with: Windows 11 Git Bash and Linux Bash
# Usage: bash scripts/test.sh [pytest arguments]
# ==============================================================================

set -eo pipefail

echo "=================================================================="
echo " Executing Automated Test Suite with Pytest"
echo "=================================================================="

# 1. Activate Virtual Environment if available
if [ -f ".venv/Scripts/activate" ]; then
    # shellcheck disable=SC1091
    source ".venv/Scripts/activate"
elif [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

# 2. Resolve Python and Pytest Availability
if [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON_BIN=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "ERROR: Python is not installed. Please run 'bash scripts/setup.sh'." >&2
    exit 1
fi

if ! "$PYTHON_BIN" -m pytest --version >/dev/null 2>&1; then
    echo "ERROR: pytest is not installed. Please run 'bash scripts/setup.sh'." >&2
    exit 1
fi

# 3. Execute Pytest with Verbose Output and Return Actual Exit Code
echo "[*] Running tests under tests/ directory..."
"$PYTHON_BIN" -m pytest tests/ -v --tb=short "$@"
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "=================================================================="
    echo " [✓] ALL TESTS PASSED SUCCESSFULLY!"
    echo "=================================================================="
else
    echo "=================================================================="
    echo " [✗] ONE OR MORE TESTS FAILED! (Exit code: $TEST_EXIT_CODE)"
    echo "=================================================================="
fi

exit $TEST_EXIT_CODE
