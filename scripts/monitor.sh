#!/usr/bin/env bash
# ==============================================================================
# Standalone Health Probe
# Checks the environment; process-local application metrics are not shared here.
# Compatible with: Windows 11 Git Bash and Linux Bash
# Usage: bash scripts/monitor.sh [--loop] [--interval 10]
# ==============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

MONITOR_LOG="logs/monitor_health.log"
mkdir -p logs

echo "=================================================================="
echo " Starting RedBus Standalone Health Probe"
echo "=================================================================="

# Check Python command
PYTHON_BIN=""
if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "ERROR: Python is not available in PATH." >&2
    exit 1
fi

LOOP_MODE=false
INTERVAL=10

while [[ $# -gt 0 ]]; do
    case "$1" in
        --loop)
            LOOP_MODE=true
            shift
            ;;
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

record_health_probe() {
    local ts
    ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

    local status="HEALTHY"
    # Execute health check script silently to verify environment
    if ! bash scripts/health_check.sh >/dev/null 2>&1; then
        status="DEGRADED"
    fi

    local log_entry="[${ts}] STATUS=${status} METRICS=unavailable (standalone process; not shared with app)"
    echo "$log_entry" >> "${MONITOR_LOG}"
    echo " [${ts}] Health Probe: ${status} | Logged to ${MONITOR_LOG}"

    if [ "$status" = "HEALTHY" ]; then
        return 0
    else
        return 1
    fi
}

if [ "$LOOP_MODE" = true ]; then
    echo "[*] Monitoring service running in continuous loop (interval: ${INTERVAL}s)..."
    echo "[*] Press Ctrl+C to terminate."
    while true; do
        record_health_probe || true
        sleep "$INTERVAL"
    done
else
    echo "[*] Executing one-shot autonomic monitoring health check..."
    record_health_probe
    EXIT_CODE=$?
    echo "=================================================================="
    if [ $EXIT_CODE -eq 0 ]; then
        echo " [✓] System is operational and healthy."
    else
        echo " [!] System health probe detected degraded state."
    fi
    echo "=================================================================="
    exit $EXIT_CODE
fi
