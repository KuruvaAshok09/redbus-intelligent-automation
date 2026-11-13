#!/usr/bin/env bash
# ==============================================================================
# Operational Backup Script
# Creates timestamped archives of logs, audit reports, and simulated catalogs
# Compatible with: Windows 11 Git Bash and Linux Bash
# Usage: bash scripts/backup.sh
# ==============================================================================

set -euo pipefail

echo "=================================================================="
echo " Initiating RedBus Autonomics Platform System Backup"
echo "=================================================================="

# Root directory detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

BACKUP_ROOT="backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET_BACKUP_DIR="${BACKUP_ROOT}/backup_${TIMESTAMP}"

# Safeguard: do not overwrite existing backups
if [ -d "${TARGET_BACKUP_DIR}" ]; then
    echo "ERROR: Backup directory ${TARGET_BACKUP_DIR} already exists. Aborting to prevent overwrite." >&2
    exit 1
fi

echo "[*] Creating backup target directory: ${TARGET_BACKUP_DIR}"
mkdir -p "${TARGET_BACKUP_DIR}/logs"
mkdir -p "${TARGET_BACKUP_DIR}/reports"
mkdir -p "${TARGET_BACKUP_DIR}/data"

# 1. Back up data catalogs
echo "[*] Backing up mock catalog datasets..."
if [ -d "data" ]; then
    cp -r data/*.json "${TARGET_BACKUP_DIR}/data/" 2>/dev/null || true
    echo "  [✓] Catalog data backed up."
fi

# 2. Back up execution telemetry logs (excluding credentials/secrets)
echo "[*] Backing up execution telemetry logs..."
if [ -d "logs" ]; then
    find logs -maxdepth 1 -name "*.jsonl" -o -name "*.log" | while read -r log_file; do
        cp "$log_file" "${TARGET_BACKUP_DIR}/logs/" 2>/dev/null || true
    done
    echo "  [✓] Logs backed up."
fi

# 3. Back up compliance reports
echo "[*] Backing up audit reports..."
if [ -d "reports" ]; then
    find reports -maxdepth 1 -name "*.json" -o -name "*.csv" -o -name "*.jsonl" | while read -r rep_file; do
        cp "$rep_file" "${TARGET_BACKUP_DIR}/reports/" 2>/dev/null || true
    done
    echo "  [✓] Reports backed up."
fi

# 4. Generate Backup Manifest
MANIFEST_FILE="${TARGET_BACKUP_DIR}/manifest.json"
cat <<EOF > "${MANIFEST_FILE}"
{
  "backup_id": "backup_${TIMESTAMP}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "source_directory": "${ROOT_DIR}",
  "status": "COMPLETED",
  "files_archived": $(find "${TARGET_BACKUP_DIR}" -type f | wc -l)
}
EOF

echo "=================================================================="
echo " [✓] BACKUP COMPLETED SUCCESSFULLY!"
echo " Location: ${TARGET_BACKUP_DIR}"
echo " Manifest: ${MANIFEST_FILE}"
echo " Total files archived: $(find "${TARGET_BACKUP_DIR}" -type f | wc -l)"
echo "=================================================================="
exit 0
