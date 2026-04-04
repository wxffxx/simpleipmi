#!/bin/bash
# =============================================================
# SI BMC — Force DWC3 into Device/Peripheral mode
# For Orange Pi CM4 (RK3566) — fcc00000.dwc3
#
# Run as root: sudo bash fix_otg.sh
# =============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[ERR]${NC} $1"; }

DWC3_DEBUGFS="/sys/kernel/debug/usb/fcc00000.dwc3"
DWC3_SYSFS="/sys/devices/platform/usbdrd/fcc00000.dwc3"

echo "=== SI BMC: USB OTG Fix for RK3566 ==="
echo ""

# Check current mode
if [ -f "$DWC3_DEBUGFS/mode" ]; then
    CURRENT=$(cat "$DWC3_DEBUGFS/mode" 2>/dev/null)
    echo "Current DWC3 mode: $CURRENT"
else
    log_error "Cannot read DWC3 debugfs mode"
    echo "Trying to mount debugfs..."
    mount -t debugfs none /sys/kernel/debug 2>/dev/null || true
    CURRENT=$(cat "$DWC3_DEBUGFS/mode" 2>/dev/null || echo "unknown")
    echo "Current DWC3 mode: $CURRENT"
fi

# Method 1: Try debugfs mode switch
echo ""
echo "--- Method 1: debugfs mode switch ---"
if echo "device" > "$DWC3_DEBUGFS/mode" 2>/dev/null; then
    sleep 2
    NEW_MODE=$(cat "$DWC3_DEBUGFS/mode" 2>/dev/null)
    echo "New DWC3 mode: $NEW_MODE"

    UDC=$(ls /sys/class/udc/ 2>/dev/null)
    if [ -n "$UDC" ]; then
        log_info "UDC found: $UDC"
        log_info "DWC3 successfully switched to device mode!"
        echo ""
        echo "Now run: sudo bash /opt/si-bmc/setup_gadget.sh setup"
        exit 0
    else
        log_warn "Mode changed but no UDC appeared, trying method 2..."
    fi
else
    log_warn "debugfs mode switch failed, trying method 2..."
fi

# Method 2: Unbind from xhci, rebind as gadget
echo ""
echo "--- Method 2: Driver rebind ---"

# Unbind xhci-hcd (host controller)
XHCI_DEV=$(ls "$DWC3_SYSFS/" 2>/dev/null | grep "xhci-hcd")
if [ -n "$XHCI_DEV" ]; then
    echo "Unbinding XHCI host: $XHCI_DEV"
    echo "$XHCI_DEV" > /sys/bus/platform/drivers/xhci-hcd/unbind 2>/dev/null || true
    sleep 1
fi

# Try unbinding and rebinding dwc3
echo "Rebinding DWC3 controller..."
echo "fcc00000.dwc3" > /sys/bus/platform/drivers/dwc3/unbind 2>/dev/null || true
sleep 1
echo "fcc00000.dwc3" > /sys/bus/platform/drivers/dwc3/bind 2>/dev/null || true
sleep 2

UDC=$(ls /sys/class/udc/ 2>/dev/null)
if [ -n "$UDC" ]; then
    log_info "UDC found after rebind: $UDC"
    exit 0
fi

# Method 3: Suggest device tree overlay
echo ""
echo "--- Method 3: Device Tree Overlay (manual) ---"
log_warn "Automatic methods failed."
echo ""
echo "You need to change dr_mode from 'otg' to 'peripheral' in the device tree."
echo ""
echo "Option A: Edit /boot/orangepiEnv.txt and add a DT overlay:"
echo "  1. Create overlay file (see below)"
echo "  2. Add to /boot/orangepiEnv.txt:"
echo "     overlays=dwc3-peripheral"
echo ""
echo "Option B: Modify the DTB directly:"
echo "  sudo apt install device-tree-compiler"
echo "  # Find the DTB:"
echo "  ls /boot/dtb/rockchip/rk3566*.dtb"
echo "  # Decompile:"
echo "  dtc -I dtb -O dts -o /tmp/rk3566.dts /boot/dtb/rockchip/rk3566-orangepi-cm4.dtb"
echo "  # Edit /tmp/rk3566.dts, find dwc3@fcc00000 and change:"
echo "  #   dr_mode = \"otg\";  →  dr_mode = \"peripheral\";"
echo "  # Recompile:"
echo "  dtc -I dts -O dtb -o /boot/dtb/rockchip/rk3566-orangepi-cm4.dtb /tmp/rk3566.dts"
echo "  # Reboot"
echo ""
