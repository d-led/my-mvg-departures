#!/bin/bash
# Power optimization script for Raspberry Pi 2 running MVG Departures Inky Display
# Run with: sudo ./scripts/optimize-pi-power.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/.pi-power-backup"
BACKUP_FILE="${BACKUP_DIR}/backup-$(date +%Y%m%d-%H%M%S).json"

echo "=== Raspberry Pi 2 Power Optimization ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script requires root privileges. Use: sudo $0"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "Creating backup of current state..."
# Save current CPU governor
CURRENT_GOV=""
if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
    CURRENT_GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
fi

# Save which services are currently enabled
ENABLED_SERVICES=()
for service in avahi-daemon.service colord.service cups.service cups-browsed.service \
               lightdm.service ModemManager.service nfs-blkmap.service rpcbind.service; do
    if systemctl is-enabled "$service" >/dev/null 2>&1; then
        ENABLED_SERVICES+=("$service")
    fi
done

# Save config.txt
CONFIG_FILE="/boot/config.txt"
CONFIG_BACKUP="${BACKUP_DIR}/config.txt.backup"
if [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$CONFIG_BACKUP"
fi

# Write backup file
{
    echo "CPU_GOVERNOR=${CURRENT_GOV}"
    echo "ENABLED_SERVICES=$(IFS=','; echo "${ENABLED_SERVICES[*]}")"
    echo "BACKUP_DATE=$(date -Iseconds)"
} > "$BACKUP_FILE"

echo "  Backup saved to: $BACKUP_FILE"
echo "  Config backup: $CONFIG_BACKUP"
echo "  To restore: sudo ./scripts/restore-pi-power.sh"
echo ""

# Services to disable (not needed for headless Inky display)
SERVICES_TO_DISABLE=(
    #"avahi-daemon.service"      # mDNS/DNS-SD (KEEP ENABLED - needed for network discovery)
    "colord.service"            # Color profiles (not needed for e-ink)
    "cups.service"              # Printing (not needed)
    "cups-browsed.service"       # Remote printer browsing (not needed)
    "lightdm.service"           # Display manager (BIG power saver - not needed for headless)
    "ModemManager.service"       # Modem management (not needed)
    "nfs-blkmap.service"        # NFS block layout (probably not needed)
    "rpcbind.service"           # RPC portmapper (probably not needed)
)

echo "1. Disabling unnecessary services..."
for service in "${SERVICES_TO_DISABLE[@]}"; do
    if systemctl is-enabled "$service" >/dev/null 2>&1; then
        echo "  Disabling $service..."
        systemctl disable "$service" --now || echo "    Warning: Failed to disable $service"
    else
        echo "  $service already disabled"
    fi
done

echo ""
echo "2. Setting CPU governor to 'ondemand' (balanced power/performance)..."
if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
    CURRENT_GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
    if [ "$CURRENT_GOV" != "ondemand" ]; then
        echo "  Current governor: $CURRENT_GOV"
        echo "  Setting to ondemand..."
        echo ondemand > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor || echo "    Warning: Failed to set governor"
    else
        echo "  Already set to ondemand"
    fi
else
    echo "  Warning: CPU frequency scaling not available"
fi

echo ""
echo "3. Limiting journal size to save disk I/O..."
journalctl --vacuum-size=50M || echo "  Warning: Failed to limit journal size"

echo ""
echo "4. Checking /boot/config.txt for power optimizations..."
CONFIG_FILE="/boot/config.txt"
if [ -f "$CONFIG_FILE" ]; then
    # Disable HDMI if not already disabled
    if ! grep -q "^hdmi_blanking=1" "$CONFIG_FILE" 2>/dev/null; then
        echo "  Adding hdmi_blanking=1 to disable HDMI..."
        echo "" >> "$CONFIG_FILE"
        echo "# Power optimization: disable HDMI" >> "$CONFIG_FILE"
        echo "hdmi_blanking=1" >> "$CONFIG_FILE"
    else
        echo "  HDMI blanking already configured"
    fi
    
    # Disable audio if not already disabled
    if ! grep -q "^dtparam=audio=off" "$CONFIG_FILE" 2>/dev/null; then
        echo "  Adding dtparam=audio=off to disable audio..."
        echo "" >> "$CONFIG_FILE"
        echo "# Power optimization: disable audio" >> "$CONFIG_FILE"
        echo "dtparam=audio=off" >> "$CONFIG_FILE"
    else
        echo "  Audio already disabled"
    fi
else
    echo "  Warning: $CONFIG_FILE not found"
fi

echo ""
echo "=== Optimization Complete ==="
echo ""
echo "Summary of changes:"
echo "  - Disabled unnecessary services (avahi, colord, cups, lightdm, etc.)"
echo "  - Set CPU governor to 'ondemand'"
echo "  - Limited journal size to 50MB"
echo "  - Configured HDMI and audio settings in /boot/config.txt"
echo ""
echo "IMPORTANT: Reboot required for /boot/config.txt changes to take effect:"
echo "  sudo reboot"
echo ""
echo "To check power status, run:"
echo "  ./scripts/powertest.sh"
echo ""
echo "To increase refresh interval (saves more power), edit my.config.toml:"
echo "  [inky]"
echo "  refresh_interval_seconds = 120  # Update every 2 minutes instead of 1"
