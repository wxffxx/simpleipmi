#!/bin/bash
# =============================================================
# SI BMC — Full Installation Script
# For fresh Orange Pi CM4 (RK3566) boards
#
# Handles: dependencies, DTB patching, ADB gadget removal,
#          HID gadget setup, service installation
#
# Run as root: sudo bash scripts/install.sh
# =============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_step()  { echo -e "${CYAN}[→]${NC} $1"; }
log_error() { echo -e "${RED}[✕]${NC} $1"; }

INSTALL_DIR="/opt/si-bmc"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NEED_REBOOT=false

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     SI BMC Server — Full Installation        ║${NC}"
echo -e "${CYAN}║     Orange Pi CM4 (RK3566)                   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Check root ───────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    log_error "Please run as root: sudo bash $0"
    exit 1
fi

# ═════════════════════════════════════════════════════════════════
# PHASE 1: System Dependencies
# ═════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}═══ Phase 1: System Dependencies ═══${NC}"

log_step "Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-dev \
    v4l-utils \
    libgpiod-dev gpiod \
    device-tree-compiler \
    2>/dev/null

log_info "System packages installed"

# ── Python dependencies ──────────────────────────────────────────
log_step "Installing Python dependencies..."
pip3 install --break-system-packages -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null || \
pip3 install -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null
log_info "Python packages installed"

# ═════════════════════════════════════════════════════════════════
# PHASE 2: DTB Patching (USB OTG → Peripheral Mode)
# ═════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}═══ Phase 2: USB Device Tree Configuration ═══${NC}"

patch_dtb_file() {
    local dtb="$1"
    if [ ! -f "$dtb" ]; then return 1; fi

    local current_mode=$(fdtget "$dtb" /usbdrd/dwc3@fcc00000 dr_mode 2>/dev/null)
    if [ -z "$current_mode" ]; then
        log_warn "  No dwc3@fcc00000 node in $dtb (skipping)"
        return 1
    fi

    if [ "$current_mode" = "peripheral" ]; then
        log_info "  $dtb — already peripheral"
        return 0
    fi

    log_step "  Patching $dtb (${current_mode} → peripheral)"

    # Backup
    cp "$dtb" "${dtb}.bak.$(date +%Y%m%d)" 2>/dev/null || true

    # Change dr_mode to peripheral
    fdtput -t s "$dtb" /usbdrd/dwc3@fcc00000 dr_mode peripheral

    # Remove extcon (prevents OTG role switch conflicts)
    fdtput -d "$dtb" /usbdrd/dwc3@fcc00000 extcon 2>/dev/null || true

    # Verify
    local new_mode=$(fdtget "$dtb" /usbdrd/dwc3@fcc00000 dr_mode 2>/dev/null)
    if [ "$new_mode" = "peripheral" ]; then
        log_info "  Patched OK: $new_mode"
        NEED_REBOOT=true
    else
        log_error "  Patch failed for $dtb"
    fi
}

# Check current running dr_mode
CURRENT_DR=$(cat /proc/device-tree/usbdrd/dwc3@fcc00000/dr_mode 2>/dev/null | tr -d '\0')
echo "Current running dr_mode: ${CURRENT_DR:-unknown}"

if [ "$CURRENT_DR" = "peripheral" ]; then
    log_info "DTB already configured correctly"
else
    log_step "Patching all CM4 DTB files..."

    # Patch all possible DTB locations
    for dtb_dir in /boot/dtb/rockchip /boot/dtb-*/rockchip; do
        if [ ! -d "$dtb_dir" ]; then continue; fi
        for dtb in "$dtb_dir"/rk3566-orangepi-cm4*.dtb; do
            patch_dtb_file "$dtb"
        done
    done
fi

# ═════════════════════════════════════════════════════════════════
# PHASE 3: Disable Competing USB Gadgets
# ═════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}═══ Phase 3: Disable Competing USB Services ═══${NC}"

# Disable the default rockchip ADB/USB gadget service
for svc in usbdevice.service usb-gadget.service adbd.service; do
    if systemctl list-unit-files "$svc" &>/dev/null 2>&1; then
        if systemctl is-enabled "$svc" &>/dev/null 2>&1; then
            log_step "Disabling $svc..."
            systemctl stop "$svc" 2>/dev/null || true
            systemctl disable "$svc" 2>/dev/null || true
            systemctl mask "$svc" 2>/dev/null || true
            log_info "$svc disabled and masked"
        else
            log_info "$svc already disabled"
        fi
    fi
done

# Evict any currently bound competing gadgets
GADGET_BASE="/sys/kernel/config/usb_gadget"
if [ -d "$GADGET_BASE" ]; then
    for g in "$GADGET_BASE"/*/; do
        gname=$(basename "$g")
        if [ "$gname" = "si_bmc" ] || [ "$gname" = "*" ]; then continue; fi
        bound=$(cat "$g/UDC" 2>/dev/null | tr -d '[:space:]')
        if [ -n "$bound" ]; then
            log_step "Evicting gadget '$gname' from UDC $bound"
            echo "" > "$g/UDC" 2>/dev/null || true
            sleep 1
            log_info "Evicted '$gname'"
        fi
    done
fi

# ═════════════════════════════════════════════════════════════════
# PHASE 4: Install Application Files
# ═════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}═══ Phase 4: Install Application ═══${NC}"

log_step "Installing to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/setup_gadget.sh"
chmod +x "$INSTALL_DIR/scripts/"*.sh 2>/dev/null || true
log_info "Files installed to $INSTALL_DIR"

# ═════════════════════════════════════════════════════════════════
# PHASE 5: Setup USB HID Gadget
# ═════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}═══ Phase 5: USB HID Gadget Setup ═══${NC}"

if [ "$CURRENT_DR" = "peripheral" ]; then
    # dr_mode is already peripheral, try setting up gadget now
    bash "$INSTALL_DIR/setup_gadget.sh" setup && {
        log_info "HID Gadget created successfully"
        ls -la /dev/hidg* 2>/dev/null
    } || {
        log_warn "Gadget setup failed (may need reboot first)"
    }
else
    log_warn "USB Gadget setup deferred — reboot required for DTB changes"
fi

# ═════════════════════════════════════════════════════════════════
# PHASE 6: Install systemd Service
# ═════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}═══ Phase 6: Systemd Service ═══${NC}"

log_step "Installing si_bmc.service..."
cp "$INSTALL_DIR/si_bmc.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable si_bmc.service
log_info "Service installed and enabled"

# Start service if DTB is already correct
if [ "$CURRENT_DR" = "peripheral" ]; then
    systemctl restart si_bmc 2>/dev/null && \
        log_info "Service started" || \
        log_warn "Service start failed, check: journalctl -u si_bmc -f"
fi

# ═════════════════════════════════════════════════════════════════
# PHASE 7: Pre-flight Checks
# ═════════════════════════════════════════════════════════════════
echo -e "\n${CYAN}═══ Phase 7: Pre-flight Checks ═══${NC}"

# Video device
if [ -e /dev/video0 ]; then
    v4l2-ctl --device=/dev/video0 --all 2>/dev/null | head -5
    log_info "Video device /dev/video0 found (MS2109)"
else
    log_warn "/dev/video0 not found — connect MS2109 capture card"
fi

# GPIO
if [ -d /sys/class/gpio ]; then
    log_info "GPIO sysfs available"
else
    log_warn "GPIO sysfs not available"
fi

# HID devices
if [ -e /dev/hidg0 ] && [ -e /dev/hidg1 ]; then
    log_info "HID devices ready: /dev/hidg0 (keyboard), /dev/hidg1 (mouse)"
else
    log_warn "HID devices not yet available (reboot may be required)"
fi

# Firewall
if command -v ufw &>/dev/null; then
    ufw allow 8080/tcp 2>/dev/null || true
    log_info "Firewall: port 8080 opened"
fi

# ═════════════════════════════════════════════════════════════════
# Done
# ═════════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Installation Complete!                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

if [ "$NEED_REBOOT" = true ]; then
    echo -e "  ${YELLOW}⚠  REBOOT REQUIRED for USB OTG changes!${NC}"
    echo -e "  Run: ${CYAN}sudo reboot${NC}"
    echo ""
    echo -e "  After reboot, the service will auto-start."
    echo -e "  Verify: ${CYAN}sudo systemctl status si_bmc${NC}"
else
    echo -e "  Service:  ${CYAN}sudo systemctl status si_bmc${NC}"
    echo -e "  Logs:     ${CYAN}sudo journalctl -u si_bmc -f${NC}"
fi

echo -e "  Access:   ${CYAN}http://$(hostname -I | awk '{print $1}'):8080${NC}"
echo ""
