#!/bin/bash
# Script to restore firmware files from bootfs to rootfs /boot/firmware
# This should fix the boot issue where /boot/firmware is empty

set -euo pipefail

BOOTFS="/Volumes/bootfs"
ROOTFS="/Volumes/rootfs"
FIRMWARE_DIR="${ROOTFS}/boot/firmware"

echo "Restoring firmware files from ${BOOTFS} to ${FIRMWARE_DIR}..."
echo ""

# Check if directories exist
if [ ! -d "$BOOTFS" ]; then
    echo "Error: Boot partition not found at ${BOOTFS}" >&2
    exit 1
fi

if [ ! -d "$ROOTFS" ]; then
    echo "Error: Root filesystem not found at ${ROOTFS}" >&2
    exit 1
fi

# Check if we can write to firmware directory
if [ ! -w "$FIRMWARE_DIR" ]; then
    echo "Error: Cannot write to ${FIRMWARE_DIR}" >&2
    echo "You may need to run this script with sudo or adjust permissions" >&2
    exit 1
fi

# Essential firmware files to copy
ESSENTIAL_FILES=(
    "config.txt"
    "cmdline.txt"
    "start.elf"
    "start4.elf"
    "start4cd.elf"
    "start4db.elf"
    "start4x.elf"
    "fixup.dat"
    "fixup4.dat"
    "fixup4cd.dat"
    "fixup4db.dat"
    "fixup4x.dat"
    "bootcode.bin"
    "kernel.img"
    "kernel7.img"
    "kernel8.img"
)

# Copy essential files
echo "Copying essential firmware files..."
for file in "${ESSENTIAL_FILES[@]}"; do
    if [ -f "${BOOTFS}/${file}" ]; then
        echo "  Copying ${file}..."
        cp "${BOOTFS}/${file}" "${FIRMWARE_DIR}/${file}"
    else
        echo "  Warning: ${file} not found in bootfs" >&2
    fi
done

# Copy all .elf, .dat, .bin files (firmware files)
echo ""
echo "Copying all firmware binaries..."
find "$BOOTFS" -maxdepth 1 -type f \( -name "*.elf" -o -name "*.dat" -o -name "*.bin" \) -exec cp {} "$FIRMWARE_DIR/" \;

# Copy overlays directory if it exists
if [ -d "${BOOTFS}/overlays" ]; then
    echo "Copying overlays directory..."
    if [ -d "${FIRMWARE_DIR}/overlays" ]; then
        cp -r "${BOOTFS}/overlays"/* "${FIRMWARE_DIR}/overlays/"
    else
        cp -r "${BOOTFS}/overlays" "${FIRMWARE_DIR}/"
    fi
fi

# Copy any other important files
OTHER_FILES=("issue.txt")
for file in "${OTHER_FILES[@]}"; do
    if [ -f "${BOOTFS}/${file}" ]; then
        echo "  Copying ${file}..."
        cp "${BOOTFS}/${file}" "${FIRMWARE_DIR}/${file}"
    fi
done

echo ""
echo "✓ Firmware files restored successfully!"
echo ""
echo "Files copied to: ${FIRMWARE_DIR}"
echo ""
echo "Next steps:"
echo "1. Verify the files are in place: ls -la ${FIRMWARE_DIR}"
echo "2. Check that config.txt and cmdline.txt are correct"
echo "3. Try booting the Raspberry Pi"
echo ""
