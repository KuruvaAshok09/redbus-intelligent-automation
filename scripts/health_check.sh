#!/usr/bin/env bash
# ==============================================================================
# System & Environment Health Check Script
# Compatible with: Windows 11 Git Bash and Linux Bash
# ==============================================================================

set -uo pipefail

echo "=================================================================="
echo " RedBus Automation Platform - Operational Health Audit"
echo "=================================================================="

HEALTH_FAILURES=0

check_status() {
    local label="$1"
    local status="$2"
    local details="$3"
    if [ "$status" -eq 0 ]; then
        printf " [✓ PASS] %-30s : %s\n" "$label" "$details"
    else
        printf " [✗ FAIL] %-30s : %s\n" "$label" "$details"
        HEALTH_FAILURES=$((HEALTH_FAILURES + 1))
    fi
}

# 1. Python Availability
if [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON_BIN=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v py >/dev/null 2>&1; then
    PYTHON_BIN="py -3"
else
    PYTHON_BIN=""
fi

if [ -n "$PYTHON_BIN" ]; then
    PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>/dev/null || echo "unknown")
    if [ "$PY_VER" = "unknown" ]; then
        check_status "Python Environment" 1 "Python detected but could not execute"
    else
        check_status "Python Environment" 0 "Found Python $PY_VER"
    fi
else
    check_status "Python Environment" 1 "Python executable not found in PATH"
fi

# 2. Required Directories
for dir in "redbus_automation" "data" "logs" "reports" "tests" "scripts" "docs" ".github/workflows"; do
    if [ -d "$dir" ]; then
        check_status "Directory: $dir" 0 "Present"
    else
        check_status "Directory: $dir" 1 "Missing directory"
    fi
done

# 3. Sample JSON Data File
DATA_FILE="data/sample_buses.json"
if [ -f "$DATA_FILE" ]; then
    if [ -n "$PYTHON_BIN" ]; then
        BUS_COUNT=$($PYTHON_BIN -c "import json; print(len(json.load(open('$DATA_FILE'))))" 2>/dev/null || echo "0")
    else
        BUS_COUNT="0"
    fi
    if [ "$BUS_COUNT" -ge 15 ]; then
        check_status "Primary Catalog Dataset" 0 "Verified ($BUS_COUNT simulated buses)"
    else
        check_status "Primary Catalog Dataset" 1 "Dataset has fewer than 15 buses ($BUS_COUNT)"
    fi
else
    check_status "Primary Catalog Dataset" 1 "Missing $DATA_FILE"
fi

# 4. Fallback Catalog Data File
FALLBACK_FILE="data/fallback_buses.json"
if [ -f "$FALLBACK_FILE" ]; then
    if [ -n "$PYTHON_BIN" ]; then
        FB_COUNT=$($PYTHON_BIN -c "import json; print(len(json.load(open('$FALLBACK_FILE'))))" 2>/dev/null || echo "0")
    else
        FB_COUNT="0"
    fi
    if [ "$FB_COUNT" -gt 0 ]; then
        check_status "Fallback Catalog Dataset" 0 "Verified ($FB_COUNT fallback buses)"
    else
        check_status "Fallback Catalog Dataset" 1 "Fallback catalog empty"
    fi
else
    check_status "Fallback Catalog Dataset" 1 "Missing $FALLBACK_FILE"
fi

# 5. Dependency Imports
if [ -n "$PYTHON_BIN" ]; then
    if [ "$PYTHON_BIN" = "py -3" ]; then
        py -3 -c "import streamlit, pytest" >/dev/null 2>&1
    else
        $PYTHON_BIN -c "import streamlit, pytest" >/dev/null 2>&1
    fi
fi
check_status "External Dependencies" $? "Streamlit and Pytest verified"

# 6. Application Package Imports
if [ -n "$PYTHON_BIN" ]; then
    if [ "$PYTHON_BIN" = "py -3" ]; then
        py -3 -c "import redbus_automation; from redbus_automation import INCIDENT_MANAGER, BOOKING_ENGINE" >/dev/null 2>&1
    else
        $PYTHON_BIN -c "import redbus_automation; from redbus_automation import INCIDENT_MANAGER, BOOKING_ENGINE" >/dev/null 2>&1
    fi
fi
check_status "Core Package Import" $? "redbus_automation & engines imported cleanly"

# 7. Logging Directory Writeability
touch logs/.health_test && rm -f logs/.health_test >/dev/null 2>&1
check_status "Log Directory IO" $? "Write permissions verified on logs/"

# 8. Reports Directory Writeability
touch reports/.health_test && rm -f reports/.health_test >/dev/null 2>&1
check_status "Report Directory IO" $? "Write permissions verified on reports/"

# Summary
echo "=================================================================="
if [ "$HEALTH_FAILURES" -eq 0 ]; then
    echo " OVERALL SYSTEM HEALTH: HEALTHY (All checks passed)"
    echo "=================================================================="
    exit 0
else
    echo " OVERALL SYSTEM HEALTH: DEGRADED ($HEALTH_FAILURES check(s) failed)"
    echo "=================================================================="
    exit 1
fi
