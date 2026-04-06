#!/bin/bash
# =============================================================
# SI BMC — USB OTG HID Gadget Setup Script
# Creates a composite USB HID device (keyboard + absolute mouse)
# via Linux ConfigFS USB Gadget framework.
#
# Must be run as root on the Orange Pi CM4.
# =============================================================

set -e

GADGET_DIR="/sys/kernel/config/usb_gadget/si_bmc"
UDC_NAME=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Check prerequisites ────────────────────────────────────────
check_prerequisites() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root (sudo)"
        exit 1
    fi

    # Check configfs mount
    if ! mountpoint -q /sys/kernel/config 2>/dev/null; then
        log_info "Mounting configfs..."
        mount -t configfs none /sys/kernel/config
    fi

    # Load libcomposite module
    if ! lsmod | grep -q libcomposite; then
        log_info "Loading libcomposite kernel module..."
        modprobe libcomposite
        if [ $? -ne 0 ]; then
            log_error "Failed to load libcomposite module. Check kernel config."
            exit 1
        fi
    fi

    # Find UDC
    UDC_NAME=$(ls /sys/class/udc/ 2>/dev/null | head -1)
    if [ -z "$UDC_NAME" ]; then
        log_error "No USB Device Controller (UDC) found!"
        log_error "Make sure the USB OTG port is configured in device tree."
        exit 1
    fi
    log_info "Found UDC: $UDC_NAME"
}

# ── Evict competing gadgets (e.g. rockchip ADB gadget) ─────────
evict_competing_gadgets() {
    local gadget_base="/sys/kernel/config/usb_gadget"
    if [ ! -d "$gadget_base" ]; then return; fi

    for g in "$gadget_base"/*/; do
        local gname=$(basename "$g")
        if [ "$gname" = "si_bmc" ]; then continue; fi

        local bound_udc=$(cat "$g/UDC" 2>/dev/null | tr -d '[:space:]')
        if [ -n "$bound_udc" ]; then
            log_warn "Evicting competing gadget '$gname' (bound to $bound_udc)"
            echo "" > "$g/UDC" 2>/dev/null || true
            sleep 1
        fi
    done
}

# ── Tear down existing gadget ──────────────────────────────────
teardown() {
    if [ -d "$GADGET_DIR" ]; then
        log_info "Tearing down existing gadget..."

        # Unbind from UDC
        echo "" > "$GADGET_DIR/UDC" 2>/dev/null || true

        # Remove symlinks from configurations
        rm -f "$GADGET_DIR/configs/c.1/hid.keyboard" 2>/dev/null || true
        rm -f "$GADGET_DIR/configs/c.1/hid.mouse" 2>/dev/null || true

        # Remove strings
        rmdir "$GADGET_DIR/configs/c.1/strings/0x409" 2>/dev/null || true
        rmdir "$GADGET_DIR/configs/c.1" 2>/dev/null || true
        rmdir "$GADGET_DIR/functions/hid.keyboard" 2>/dev/null || true
        rmdir "$GADGET_DIR/functions/hid.mouse" 2>/dev/null || true
        rmdir "$GADGET_DIR/strings/0x409" 2>/dev/null || true
        rmdir "$GADGET_DIR" 2>/dev/null || true

        log_info "Previous gadget removed"
    fi
}

# ── Create HID Gadget ──────────────────────────────────────────
setup_gadget() {
    log_info "Creating USB HID composite gadget..."

    # Create gadget
    mkdir -p "$GADGET_DIR"
    cd "$GADGET_DIR"

    # Device descriptors
    echo 0x1d6b > idVendor    # Linux Foundation
    echo 0x0104 > idProduct   # Composite Device
    echo 0x0100 > bcdDevice   # v1.0.0
    echo 0x0200 > bcdUSB      # USB 2.0

    echo 0xEF > bDeviceClass
    echo 0x02 > bDeviceSubClass
    echo 0x01 > bDeviceProtocol

    # Strings
    mkdir -p strings/0x409
    echo "SI_BMC_2024" > strings/0x409/serialnumber
    echo "SI Technologies" > strings/0x409/manufacturer
    echo "SI BMC KVM HID" > strings/0x409/product

    # ── Keyboard Function ──────────────────────────────────────
    log_info "Setting up keyboard HID function..."
    mkdir -p functions/hid.keyboard
    echo 1 > functions/hid.keyboard/protocol    # 1 = Keyboard
    echo 1 > functions/hid.keyboard/subclass     # 1 = Boot Interface
    echo 8 > functions/hid.keyboard/report_length

    # Standard keyboard HID report descriptor (8 bytes per report)
    # Modifier byte + Reserved + 6 key codes
    echo -ne '\x05\x01'         > functions/hid.keyboard/report_desc  # USAGE_PAGE (Generic Desktop)
    echo -ne '\x09\x06'        >> functions/hid.keyboard/report_desc  # USAGE (Keyboard)
    echo -ne '\xa1\x01'        >> functions/hid.keyboard/report_desc  # COLLECTION (Application)

    # Modifier keys (1 byte)
    echo -ne '\x05\x07'        >> functions/hid.keyboard/report_desc  #   USAGE_PAGE (Keyboard)
    echo -ne '\x19\xe0'        >> functions/hid.keyboard/report_desc  #   USAGE_MINIMUM (Left Control)
    echo -ne '\x29\xe7'        >> functions/hid.keyboard/report_desc  #   USAGE_MAXIMUM (Right GUI)
    echo -ne '\x15\x00'        >> functions/hid.keyboard/report_desc  #   LOGICAL_MINIMUM (0)
    echo -ne '\x25\x01'        >> functions/hid.keyboard/report_desc  #   LOGICAL_MAXIMUM (1)
    echo -ne '\x75\x01'        >> functions/hid.keyboard/report_desc  #   REPORT_SIZE (1)
    echo -ne '\x95\x08'        >> functions/hid.keyboard/report_desc  #   REPORT_COUNT (8)
    echo -ne '\x81\x02'        >> functions/hid.keyboard/report_desc  #   INPUT (Data,Var,Abs)

    # Reserved byte
    echo -ne '\x95\x01'        >> functions/hid.keyboard/report_desc  #   REPORT_COUNT (1)
    echo -ne '\x75\x08'        >> functions/hid.keyboard/report_desc  #   REPORT_SIZE (8)
    echo -ne '\x81\x01'        >> functions/hid.keyboard/report_desc  #   INPUT (Const)

    # LEDs (output, 5 bits)
    echo -ne '\x95\x05'        >> functions/hid.keyboard/report_desc  #   REPORT_COUNT (5)
    echo -ne '\x75\x01'        >> functions/hid.keyboard/report_desc  #   REPORT_SIZE (1)
    echo -ne '\x05\x08'        >> functions/hid.keyboard/report_desc  #   USAGE_PAGE (LEDs)
    echo -ne '\x19\x01'        >> functions/hid.keyboard/report_desc  #   USAGE_MINIMUM (Num Lock)
    echo -ne '\x29\x05'        >> functions/hid.keyboard/report_desc  #   USAGE_MAXIMUM (Kana)
    echo -ne '\x91\x02'        >> functions/hid.keyboard/report_desc  #   OUTPUT (Data,Var,Abs)

    # LED padding (3 bits)
    echo -ne '\x95\x01'        >> functions/hid.keyboard/report_desc  #   REPORT_COUNT (1)
    echo -ne '\x75\x03'        >> functions/hid.keyboard/report_desc  #   REPORT_SIZE (3)
    echo -ne '\x91\x01'        >> functions/hid.keyboard/report_desc  #   OUTPUT (Const)

    # Key array (6 bytes)
    echo -ne '\x95\x06'        >> functions/hid.keyboard/report_desc  #   REPORT_COUNT (6)
    echo -ne '\x75\x08'        >> functions/hid.keyboard/report_desc  #   REPORT_SIZE (8)
    echo -ne '\x15\x00'        >> functions/hid.keyboard/report_desc  #   LOGICAL_MINIMUM (0)
    echo -ne '\x26\xff\x00'    >> functions/hid.keyboard/report_desc  #   LOGICAL_MAXIMUM (255)
    echo -ne '\x05\x07'        >> functions/hid.keyboard/report_desc  #   USAGE_PAGE (Keyboard)
    echo -ne '\x19\x00'        >> functions/hid.keyboard/report_desc  #   USAGE_MINIMUM (0)
    echo -ne '\x29\xff'        >> functions/hid.keyboard/report_desc  #   USAGE_MAXIMUM (255)
    echo -ne '\x81\x00'        >> functions/hid.keyboard/report_desc  #   INPUT (Data,Ary,Abs)

    echo -ne '\xc0'            >> functions/hid.keyboard/report_desc  # END_COLLECTION

    # ── Mouse Function (Absolute) ─────────────────────────────
    log_info "Setting up absolute mouse HID function..."
    mkdir -p functions/hid.mouse
    echo 0 > functions/hid.mouse/protocol    # 0 = None (custom)
    echo 0 > functions/hid.mouse/subclass    # 0 = No subclass
    echo 7 > functions/hid.mouse/report_length

    # Absolute mouse HID report descriptor
    # Byte 0: buttons (3 bits + 5 padding)
    # Byte 1-2: X absolute (0 - 32767, uint16 LE)
    # Byte 3-4: Y absolute (0 - 32767, uint16 LE)
    # Byte 5: Vertical wheel (int8)
    # Byte 6: Horizontal wheel (int8)
    echo -ne '\x05\x01'         > functions/hid.mouse/report_desc  # USAGE_PAGE (Generic Desktop)
    echo -ne '\x09\x02'        >> functions/hid.mouse/report_desc  # USAGE (Mouse)
    echo -ne '\xa1\x01'        >> functions/hid.mouse/report_desc  # COLLECTION (Application)
    echo -ne '\x09\x01'        >> functions/hid.mouse/report_desc  #   USAGE (Pointer)
    echo -ne '\xa1\x00'        >> functions/hid.mouse/report_desc  #   COLLECTION (Physical)

    # Buttons (3 buttons, 5 bits padding)
    echo -ne '\x05\x09'        >> functions/hid.mouse/report_desc  #     USAGE_PAGE (Button)
    echo -ne '\x19\x01'        >> functions/hid.mouse/report_desc  #     USAGE_MINIMUM (Button 1)
    echo -ne '\x29\x03'        >> functions/hid.mouse/report_desc  #     USAGE_MAXIMUM (Button 3)
    echo -ne '\x15\x00'        >> functions/hid.mouse/report_desc  #     LOGICAL_MINIMUM (0)
    echo -ne '\x25\x01'        >> functions/hid.mouse/report_desc  #     LOGICAL_MAXIMUM (1)
    echo -ne '\x95\x03'        >> functions/hid.mouse/report_desc  #     REPORT_COUNT (3)
    echo -ne '\x75\x01'        >> functions/hid.mouse/report_desc  #     REPORT_SIZE (1)
    echo -ne '\x81\x02'        >> functions/hid.mouse/report_desc  #     INPUT (Data,Var,Abs)
    # Padding (5 bits)
    echo -ne '\x95\x01'        >> functions/hid.mouse/report_desc  #     REPORT_COUNT (1)
    echo -ne '\x75\x05'        >> functions/hid.mouse/report_desc  #     REPORT_SIZE (5)
    echo -ne '\x81\x01'        >> functions/hid.mouse/report_desc  #     INPUT (Const)

    # X Absolute (0-32767)
    echo -ne '\x05\x01'        >> functions/hid.mouse/report_desc  #     USAGE_PAGE (Generic Desktop)
    echo -ne '\x09\x30'        >> functions/hid.mouse/report_desc  #     USAGE (X)
    echo -ne '\x15\x00'        >> functions/hid.mouse/report_desc  #     LOGICAL_MINIMUM (0)
    echo -ne '\x26\xff\x7f'    >> functions/hid.mouse/report_desc  #     LOGICAL_MAXIMUM (32767)
    echo -ne '\x75\x10'        >> functions/hid.mouse/report_desc  #     REPORT_SIZE (16)
    echo -ne '\x95\x01'        >> functions/hid.mouse/report_desc  #     REPORT_COUNT (1)
    echo -ne '\x81\x02'        >> functions/hid.mouse/report_desc  #     INPUT (Data,Var,Abs)

    # Y Absolute (0-32767)
    echo -ne '\x09\x31'        >> functions/hid.mouse/report_desc  #     USAGE (Y)
    echo -ne '\x15\x00'        >> functions/hid.mouse/report_desc  #     LOGICAL_MINIMUM (0)
    echo -ne '\x26\xff\x7f'    >> functions/hid.mouse/report_desc  #     LOGICAL_MAXIMUM (32767)
    echo -ne '\x75\x10'        >> functions/hid.mouse/report_desc  #     REPORT_SIZE (16)
    echo -ne '\x95\x01'        >> functions/hid.mouse/report_desc  #     REPORT_COUNT (1)
    echo -ne '\x81\x02'        >> functions/hid.mouse/report_desc  #     INPUT (Data,Var,Abs)

    # Vertical scroll wheel (int8)
    echo -ne '\x09\x38'        >> functions/hid.mouse/report_desc  #     USAGE (Wheel)
    echo -ne '\x15\x81'        >> functions/hid.mouse/report_desc  #     LOGICAL_MINIMUM (-127)
    echo -ne '\x25\x7f'        >> functions/hid.mouse/report_desc  #     LOGICAL_MAXIMUM (127)
    echo -ne '\x75\x08'        >> functions/hid.mouse/report_desc  #     REPORT_SIZE (8)
    echo -ne '\x95\x01'        >> functions/hid.mouse/report_desc  #     REPORT_COUNT (1)
    echo -ne '\x81\x06'        >> functions/hid.mouse/report_desc  #     INPUT (Data,Var,Rel)

    # Horizontal scroll wheel (int8)
    echo -ne '\x05\x0c'        >> functions/hid.mouse/report_desc  #     USAGE_PAGE (Consumer)
    echo -ne '\x0a\x38\x02'    >> functions/hid.mouse/report_desc  #     USAGE (AC Pan)
    echo -ne '\x15\x81'        >> functions/hid.mouse/report_desc  #     LOGICAL_MINIMUM (-127)
    echo -ne '\x25\x7f'        >> functions/hid.mouse/report_desc  #     LOGICAL_MAXIMUM (127)
    echo -ne '\x75\x08'        >> functions/hid.mouse/report_desc  #     REPORT_SIZE (8)
    echo -ne '\x95\x01'        >> functions/hid.mouse/report_desc  #     REPORT_COUNT (1)
    echo -ne '\x81\x06'        >> functions/hid.mouse/report_desc  #     INPUT (Data,Var,Rel)

    echo -ne '\xc0'            >> functions/hid.mouse/report_desc  #   END_COLLECTION (Physical)
    echo -ne '\xc0'            >> functions/hid.mouse/report_desc  # END_COLLECTION (Application)

    # ── Configuration ──────────────────────────────────────────
    log_info "Creating configuration..."
    mkdir -p configs/c.1/strings/0x409
    echo "SI BMC KVM Config" > configs/c.1/strings/0x409/configuration
    echo 250 > configs/c.1/MaxPower   # 250mA

    # Link functions to configuration
    ln -s functions/hid.keyboard configs/c.1/
    ln -s functions/hid.mouse configs/c.1/

    # ── Bind to UDC ────────────────────────────────────────────
    log_info "Binding to UDC: $UDC_NAME"
    echo "$UDC_NAME" > UDC

    log_info "USB HID Gadget created successfully!"

    # Set permissions for the HID devices
    sleep 1
    chmod 666 /dev/hidg0 2>/dev/null || log_warn "Could not set permissions on /dev/hidg0"
    chmod 666 /dev/hidg1 2>/dev/null || log_warn "Could not set permissions on /dev/hidg1"

    log_info "HID devices ready:"
    ls -la /dev/hidg* 2>/dev/null || log_warn "HID devices not yet available"
}

# ── Main ───────────────────────────────────────────────────────
case "${1:-setup}" in
    setup)
        check_prerequisites
        evict_competing_gadgets
        teardown
        setup_gadget
        ;;
    teardown)
        check_prerequisites
        teardown
        log_info "Gadget removed"
        ;;
    status)
        if [ -d "$GADGET_DIR" ]; then
            echo "Gadget: ACTIVE"
            echo "UDC: $(cat $GADGET_DIR/UDC 2>/dev/null || echo 'unbound')"
            echo "Devices:"
            ls -la /dev/hidg* 2>/dev/null || echo "  No HID devices"
        else
            echo "Gadget: NOT CONFIGURED"
        fi
        ;;
    *)
        echo "Usage: $0 {setup|teardown|status}"
        exit 1
        ;;
esac
