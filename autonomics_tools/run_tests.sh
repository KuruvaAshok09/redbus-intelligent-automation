#!/usr/bin/env bash

set -u
set -o pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

if ! cd "$PROJECT_ROOT"; then
    printf '[FAIL] Could not enter project directory: %s\n' "$PROJECT_ROOT" >&2
    exit 1
fi

if [ -x "$PROJECT_ROOT/.venv/Scripts/python.exe" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
else
    printf '[FAIL] Python was not found. Activate an environment with Python installed.\n' >&2
    exit 1
fi

if ! "$PYTHON_BIN" -m pytest --version >/dev/null 2>&1; then
    printf '[FAIL] pytest is unavailable with %s.\n' "$PYTHON_BIN" >&2
    exit 1
fi

TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/redbus-pytest.XXXXXX")" || {
    printf '[FAIL] Could not create a temporary test directory.\n' >&2
    exit 1
}
cleanup() {
    rm -rf -- "$TEST_ROOT"
}
trap cleanup EXIT

if ! cp -R "$PROJECT_ROOT/app.py" "$PROJECT_ROOT/redbus_automation" "$PROJECT_ROOT/data" "$PROJECT_ROOT/tests" "$TEST_ROOT/"; then
    printf '[FAIL] Could not prepare the isolated test copy.\n' >&2
    exit 1
fi

if ! cd "$TEST_ROOT"; then
    printf '[FAIL] Could not enter the isolated test directory.\n' >&2
    exit 1
fi

printf '[INFO] Running the existing pytest suite from an isolated temporary copy.\n'
PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -m pytest tests/ -v --tb=short -p no:cacheprovider "$@"
TEST_EXIT_CODE=$?

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
    printf '[PASS] The pytest suite completed successfully.\n'
else
    printf '[FAIL] The pytest suite exited with status %s.\n' "$TEST_EXIT_CODE" >&2
fi

exit "$TEST_EXIT_CODE"
