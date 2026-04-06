#!/bin/bash
# ============================================================
# SI BMC — Flash & Auto-Reset Script
# 
# Usage: ./flash.sh [firmware_only]
#   No args  = build + flash firmware
#   fs       = build + flash SPIFFS
#   all      = build + flash firmware + SPIFFS
# ============================================================

set -e

ESPTOOL="/Users/wxffxx/Library/Arduino15/packages/esp32/tools/esptool_py/5.1.0/esptool"
OTG_PORT="/dev/cu.usbmodem21201"
COM_PORT="/dev/cu.usbmodem59090304871"
BAUD=460800
FLASH_SIZE="8MB"
BUILD_DIR=".pio/build/esp32s3"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  SI BMC Flash Tool${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

# Check OTG port
if [ ! -e "$OTG_PORT" ]; then
    echo -e "${RED}[ERROR] OTG port not found: $OTG_PORT${NC}"
    echo -e "${YELLOW}Please enter download mode: Hold BOOT → Press RST → Release BOOT${NC}"
    exit 1
fi

# Build
echo -e "${YELLOW}[1/3] Building firmware...${NC}"
pio run 2>&1 | tail -3

MODE="${1:-firmware}"

if [ "$MODE" = "fs" ] || [ "$MODE" = "all" ]; then
    echo -e "${YELLOW}[2/3] Building & flashing SPIFFS...${NC}"
    pio run --target buildfs 2>&1 | tail -3
    $ESPTOOL --chip esp32s3 --port "$OTG_PORT" --baud $BAUD \
        --before default-reset --after no-reset \
        write-flash --flash-mode dio --flash-size $FLASH_SIZE \
        0x670000 "$BUILD_DIR/spiffs.bin"
fi

if [ "$MODE" = "firmware" ] || [ "$MODE" = "all" ]; then
    echo -e "${YELLOW}[2/3] Flashing firmware...${NC}"
    $ESPTOOL --chip esp32s3 --port "$OTG_PORT" --baud $BAUD \
        --before default-reset --after no-reset \
        write-flash --flash-mode dio --flash-size $FLASH_SIZE \
        0x0 "$BUILD_DIR/bootloader.bin" \
        0x8000 "$BUILD_DIR/partitions.bin" \
        0x10000 "$BUILD_DIR/firmware.bin"
fi

# Auto-reset via COM port RTS
echo -e "${YELLOW}[3/3] Resetting board via COM port...${NC}"
if [ -e "$COM_PORT" ]; then
    python3 -c "
import serial, time
try:
    port = serial.Serial('$COM_PORT', 115200, timeout=0.5)
    port.rts = True
    time.sleep(0.1)
    port.rts = False
    port.close()
    print('Reset OK!')
except Exception as e:
    print(f'Reset failed: {e}')
    print('Please press RST button manually.')
"
else
    echo -e "${YELLOW}COM port not found. Please press RST button manually.${NC}"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  Done! Connect to WiFi 'SI-BMC'${NC}"
echo -e "${GREEN}  Password: 12345678${NC}"  
echo -e "${GREEN}  Open: http://192.168.4.1${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
