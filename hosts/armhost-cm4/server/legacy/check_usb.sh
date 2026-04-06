#!/bin/bash
echo "=== DWC3 controller in sysfs ==="
find /sys -path "*/fcc00000*" -maxdepth 5 2>/dev/null | head -20

echo ""
echo "=== DWC3 mode ==="
cat /sys/devices/platform/fcc00000.dwc3/mode 2>/dev/null || echo "no mode file"
cat /sys/devices/platform/usbdrd/fcc00000.dwc3/mode 2>/dev/null || echo "no mode file (alt path)"

echo ""
echo "=== DWC3 role ==="
cat /sys/devices/platform/fcc00000.dwc3/role 2>/dev/null || echo "no role file"
find /sys -name "role" -path "*dwc3*" 2>/dev/null | while read f; do echo "$f: $(cat $f)"; done

echo ""
echo "=== usbdrd device tree node ==="
find /proc/device-tree/usbdrd -maxdepth 2 2>/dev/null | head -20
cat /proc/device-tree/usbdrd/status 2>/dev/null | tr '\0' ' '; echo
cat /proc/device-tree/usbdrd/dr_mode 2>/dev/null | tr '\0' ' '; echo

echo ""
echo "=== DWC3 child node ==="
find /proc/device-tree/usbdrd -name "dr_mode" 2>/dev/null | while read f; do echo "$f: $(cat $f | tr '\0' ' ')"; done
find /proc/device-tree/usbdrd -name "status"  2>/dev/null | while read f; do echo "$f: $(cat $f | tr '\0' ' ')"; done
find /proc/device-tree/usbdrd -name "compatible" 2>/dev/null | while read f; do echo "$f: $(cat $f | tr '\0' ' ')"; done

echo ""
echo "=== Try manually binding DWC3 ==="
ls /sys/bus/platform/drivers/dwc3/ 2>/dev/null

echo ""
echo "=== All platform devices with dwc/usb ==="
ls /sys/bus/platform/devices/ | grep -iE "dwc|usb" 2>/dev/null

echo ""
echo "=== Check if UDC appears after modprobe ==="
modprobe dwc3 2>/dev/null; echo "dwc3 modprobe: $?"
modprobe dwc3-of-simple 2>/dev/null; echo "dwc3-of-simple modprobe: $?"
modprobe libcomposite 2>/dev/null; echo "libcomposite modprobe: $?"
sleep 1
ls /sys/class/udc/ 2>/dev/null || echo "still empty"
