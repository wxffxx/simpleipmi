#!/bin/bash
# =============================================================
# SI BMC — Manual DTB Patch (Simple & Reliable)
# Patches dwc3@fcc00000 dr_mode from "otg" to "peripheral"
#
# Usage: sudo bash patch_dtb_v2.sh
# =============================================================
set -e

echo "=== SI BMC: DTB Patcher v2 ==="
echo ""

# Install dtc if needed
dpkg -l device-tree-compiler &>/dev/null || apt install -y device-tree-compiler

# Find ALL rk3566 DTB files
echo "--- Searching for DTB files ---"
find /boot -name "*.dtb" 2>/dev/null | while read f; do echo "  $f"; done

echo ""

# Identify the correct DTB (try common names)
DTB=""
for candidate in \
    /boot/dtb/rockchip/rk3566-orangepi-cm4.dtb \
    /boot/dtb/rockchip/rk3568-orangepi-cm4.dtb \
    /boot/dtb/rockchip/rk3566-orangepi*.dtb \
    /boot/dtb/rockchip/rk356*.dtb; do
    for f in $candidate; do
        if [ -f "$f" ]; then
            DTB="$f"
            break 2
        fi
    done
done

if [ -z "$DTB" ]; then
    echo "ERROR: No DTB found! Listing /boot:"
    find /boot -name "*.dtb" -type f 2>/dev/null
    exit 1
fi

echo "Using DTB: $DTB"
echo ""

# Backup
BACKUP="${DTB}.bak_$(date +%s)"
cp "$DTB" "$BACKUP"
echo "Backup: $BACKUP"

# Decompile
echo "Decompiling..."
dtc -I dtb -O dts -o /tmp/cm4.dts "$DTB" 2>/tmp/dtc_warnings.txt || true

# Show current dr_mode
echo ""
echo "--- Current dwc3@fcc00000 settings ---"
grep -n -A 5 'dwc3@fcc00000' /tmp/cm4.dts | grep -E 'dr_mode|extcon|status' | head -5

# Count how many times dr_mode appears
DR_COUNT=$(grep -c 'dr_mode' /tmp/cm4.dts)
echo "Total dr_mode entries in DTS: $DR_COUNT"

# Patch using python for precision
echo ""
echo "Patching..."
python3 << 'PYEOF'
with open("/tmp/cm4.dts", "r") as f:
    lines = f.readlines()

patched_dr = 0
patched_extcon = 0
in_dwc3_fcc = False
brace_depth = 0

new_lines = []
for i, line in enumerate(lines):
    # Detect entry into dwc3@fcc00000
    if "dwc3@fcc00000" in line and "{" in line:
        in_dwc3_fcc = True
        brace_depth = 1
        new_lines.append(line)
        continue
    elif "dwc3@fcc00000" in line:
        in_dwc3_fcc = True
        brace_depth = 0
        new_lines.append(line)
        continue

    if in_dwc3_fcc:
        brace_depth += line.count("{") - line.count("}")

        # Patch dr_mode
        if "dr_mode" in line and "otg" in line:
            line = line.replace('"otg"', '"peripheral"')
            patched_dr += 1
            print(f"  Line {i+1}: dr_mode patched to peripheral")

        # Remove extcon
        if "extcon" in line and "=" in line:
            patched_extcon += 1
            print(f"  Line {i+1}: removed extcon reference")
            continue  # Skip this line

        if brace_depth <= 0:
            in_dwc3_fcc = False

    new_lines.append(line)

with open("/tmp/cm4.dts", "w") as f:
    f.writelines(new_lines)

print(f"\nPatched: {patched_dr} dr_mode, {patched_extcon} extcon entries")
if patched_dr == 0:
    print("WARNING: dr_mode not found! Check DTS manually.")
PYEOF

# Show patched result
echo ""
echo "--- Patched dwc3@fcc00000 settings ---"
grep -n -A 5 'dwc3@fcc00000' /tmp/cm4.dts | grep -E 'dr_mode|extcon|status' | head -5

# Recompile
echo ""
echo "Recompiling DTB..."
dtc -I dts -O dtb -o "$DTB" /tmp/cm4.dts 2>/tmp/dtc_warnings.txt || {
    echo "ERROR: dtc failed! Restoring backup..."
    cp "$BACKUP" "$DTB"
    echo "Restored from backup."
    exit 1
}

echo ""
echo "========================================="
echo "  DTB patched successfully!"
echo "  dr_mode changed: otg -> peripheral"
echo "  extcon removed from dwc3@fcc00000"
echo ""
echo "  Backup: $BACKUP"
echo "  To restore: sudo cp $BACKUP $DTB"
echo ""
echo "  NOW REBOOT: sudo reboot"
echo "========================================="
