#!/bin/bash
# Quick power status check for Raspberry Pi
# Shows CPU governor, voltage, temperature, throttling, and running services

echo "=== Power Status ==="
if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
    echo "CPU Governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"
else
    echo "CPU Governor: (not available)"
fi

if command -v vcgencmd >/dev/null 2>&1; then
    echo "Voltage: $(vcgencmd measure_volts 2>/dev/null || echo 'N/A')"
    echo "Temperature: $(vcgencmd measure_temp 2>/dev/null || echo 'N/A')"
    echo "Throttled: $(vcgencmd get_throttled 2>/dev/null || echo 'N/A')"
    echo "CPU Freq: $(vcgencmd measure_clock arm 2>/dev/null || echo 'N/A')"
else
    echo "vcgencmd not available (not a Raspberry Pi?)"
fi

echo ""
echo "=== Running Services ==="
systemctl list-units --type=service --state=running --no-pager | head -25

echo ""
echo "=== Journal Disk Usage ==="
journalctl --disk-usage 2>/dev/null || echo "Unable to check journal size"

echo ""
echo "=== WiFi Power Management ==="
if command -v iwconfig >/dev/null 2>&1; then
    WLAN_INTERFACE=$(iwconfig 2>/dev/null | grep -o '^[^ ]*' | head -1)
    if [ -n "$WLAN_INTERFACE" ]; then
        CURRENT_POWER=$(iwconfig "$WLAN_INTERFACE" 2>/dev/null | grep -o 'Power Management:[^ ]*' || echo "off")
        echo "WiFi interface: $WLAN_INTERFACE"
        echo "Power management: $CURRENT_POWER"
        echo "  - Power management ON = saves power (default, recommended)"
        echo "  - Power management OFF = uses more power but improves connection stability"
        echo "  - To change: sudo iwconfig $WLAN_INTERFACE power off"
    else
        echo "No WiFi interface found"
    fi
else
    echo "iwconfig not available"
fi
