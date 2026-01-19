#!/bin/bash
# Restore Raspberry Pi power settings to state before optimization
# Run with: sudo ./scripts/restore-pi-power.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/.pi-power-backup"
BACKUP_FILE="${BACKUP_DIR}/backup-$(date +%Y%m%d-%H%M%S).json"

echo "=== Raspberry Pi Power Settings Restore ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script requires root privileges. Use: sudo $0"
    exit 1
fi

# Find the most recent backup
if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: No backup directory found at $BACKUP_DIR"
    echo "Cannot restore - no backup was created."
    exit 1
fi

LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/backup-*.json 2>/dev/null | head -1)
if [ -z "$LATEST_BACKUP" ]; then
    echo "Error: No backup files found in $BACKUP_DIR"
    exit 1
fi

echo "Using backup: $(basename "$LATEST_BACKUP")"
echo ""

# Parse backup file (simple JSON-like format)
# Format: key=value (one per line, with special handling for arrays)

# Services that were enabled
ENABLED_SERVICES=()
if grep -q "^ENABLED_SERVICES=" "$LATEST_BACKUP"; then
    SERVICES_LINE=$(grep "^ENABLED_SERVICES=" "$LATEST_BACKUP" | cut -d'=' -f2-)
    # Parse comma-separated list
    IFS=',' read -ra SERVICES_ARRAY <<< "$SERVICES_LINE"
    for service in "${SERVICES_ARRAY[@]}"; do
        if [ -n "$service" ]; then
            ENABLED_SERVICES+=("$service")
        fi
    done
fi

# Original CPU governor
ORIGINAL_GOVERNOR=""
if grep -q "^CPU_GOVERNOR=" "$LATEST_BACKUP"; then
    ORIGINAL_GOVERNOR=$(grep "^CPU_GOVERNOR=" "$LATEST_BACKUP" | cut -d'=' -f2-)
fi

# Original config.txt backup
CONFIG_BACKUP="${BACKUP_DIR}/config.txt.backup"
CONFIG_FILE="/boot/config.txt"

echo "1. Restoring services..."
for service in "${ENABLED_SERVICES[@]}"; do
    if systemctl list-unit-files | grep -q "^${service}"; then
        if ! systemctl is-enabled "$service" >/dev/null 2>&1; then
            echo "  Enabling $service..."
            systemctl enable "$service" || echo "    Warning: Failed to enable $service"
            # Don't start automatically - let user decide
        else
            echo "  $service already enabled"
        fi
    fi
done

echo ""
echo "2. Restoring CPU governor..."
if [ -n "$ORIGINAL_GOVERNOR" ] && [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
    CURRENT_GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
    if [ "$CURRENT_GOV" != "$ORIGINAL_GOVERNOR" ]; then
        echo "  Current governor: $CURRENT_GOV"
        echo "  Restoring to: $ORIGINAL_GOVERNOR"
        echo "$ORIGINAL_GOVERNOR" > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor || echo "    Warning: Failed to restore governor"
    else
        echo "  Already set to $ORIGINAL_GOVERNOR"
    fi
else
    echo "  No original governor recorded or CPU scaling not available"
fi

echo ""
echo "3. Restoring /boot/config.txt..."
if [ -f "$CONFIG_BACKUP" ]; then
    echo "  Restoring from backup..."
    cp "$CONFIG_BACKUP" "$CONFIG_FILE" || echo "    Warning: Failed to restore config.txt"
    echo "  Note: Changes to config.txt require a reboot to take effect"
else
    echo "  No config.txt backup found - manual restoration may be needed"
    echo "  Check $CONFIG_FILE for power optimization settings:"
    echo "    - hdmi_blanking=1"
    echo "    - dtparam=audio=off"
fi

echo ""
echo "=== Restore Complete ==="
echo ""
echo "Summary:"
echo "  - Restored service states"
echo "  - Restored CPU governor"
echo "  - Restored /boot/config.txt"
echo ""
if [ -f "$CONFIG_BACKUP" ]; then
    echo "IMPORTANT: Reboot required for /boot/config.txt changes to take effect:"
    echo "  sudo reboot"
fi
echo ""
echo "Note: Services were enabled but not started. To start them:"
for service in "${ENABLED_SERVICES[@]}"; do
    echo "  sudo systemctl start $service"
done
