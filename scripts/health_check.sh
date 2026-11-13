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
if command -v python >/dev/null 2>&1; then
    PY_VER=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
    check_status "Python Environment" 0 "Found Python $PY_VER"
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
    BUS_COUNT=$(python -c "import json; print(len(json.load(open('$DATA_FILE'))))" 2>/dev/null || echo "0")
    if [ "$BUS_COUNT" -ge 15 ]; then
        check_status "Catalog Dataset" 0 "Verified ($BUS_COUNT simulated buses)"
    else
        check_status "Catalog Dataset" 1 "Dataset has fewer than 15 buses ($BUS_COUNT)"
    fi
else
    check_status "Catalog Dataset" 1 "Missing $DATA_FILE"
fi

# 4. Dependency Imports
python -c "import streamlit, pytest" >/dev/null 2>&1
check_status "External Dependencies" $? "Streamlit and Pytest verified"

# 5. Application Package Imports
python -c "import redbus_automation" >/dev/null 2>&1
check_status "Core Package Import" $? "redbus_automation imported cleanly"

# 6. Logging Directory Writeability
touch logs/.health_test && rm -f logs/.health_test >/dev/null 2>&1
check_status "Log Directory IO" $? "Write permissions verified on logs/"

# 7. Reports Directory Writeability
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
