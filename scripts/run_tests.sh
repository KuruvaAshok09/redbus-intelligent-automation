#!/usr/bin/env bash
# ==============================================================================
# Automated Test Runner Script
# Compatible with: Windows 11 Git Bash and Linux Bash
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

# 2. Check Pytest Availability
if ! command -v pytest >/dev/null 2>&1 && ! python -m pytest --version >/dev/null 2>&1; then
    echo "ERROR: pytest is not installed. Please run 'bash scripts/setup.sh'." >&2
    exit 1
fi

# 3. Execute Pytest with Verbose Output and Return Actual Exit Code
echo "[*] Running tests under tests/ directory..."
python -m pytest tests/ -v --tb=short "$@"
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
