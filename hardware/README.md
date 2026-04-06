# SI BMC — Hardware Designs

硬件设计按功能分为 5 大类。

## 目录总览

| 分类 | 目录 | 说明 |
|------|------|------|
| **KM 键鼠模块** | `km/` | USB HID 键盘/鼠标模拟板卡 |
| **KVM 载板** | `kvm-carrier/` | 承载 SoC/CM 核心模块的主板 |
| **视频采集** | `video-capture/` | HDMI 输入/转 CSI/USB 采集模块 |
| **核心板** | `coreboard/` | SoC 核心模块设计 |
| **配件** | `accessories/` | 继电器等辅助功能模块 |

---

## 模块状态

| 模块 | 路径 | 状态 | 备注 |
|------|------|------|------|
| KM ESP32-S2 v1 | `km/esp32s2/v1-integrated/` | ⚠️ DEPRECATED | 已被 XIAO ESP32-S3 方案替代 |
| KM ESP32-S2 v2 | `km/esp32s2/v2-external-burner/` | ⚠️ DEPRECATED | 已被 XIAO ESP32-S3 方案替代 |
| KM XIAO ESP32-S3 | `km/xiao-esp32s3/` | ✅ ACTIVE | 当前推荐 KM 方案 |
| KM STM32F103 | `km/stm32f103/` | 🧪 EXPERIMENTAL | 有硬件设计，固件开发中 |
| KVM PCIe CM4 v1 | `kvm-carrier/pciecm4-v1/` | ⚠️ DEPRECATED | 已被 v2 替代 |
| KVM PCIe CM4 v2 | `kvm-carrier/pciecm4-v2/` | ✅ ACTIVE | 当前主力载板 |
| KVM T113 | `kvm-carrier/t113/` | 🧪 EXPERIMENTAL | 早期探索方案 |
| HDMI2CSI Toshiba | `video-capture/hdmi2csi-toshiba/` | ✅ ACTIVE | TC358743 方案，完整设计 |
| HDMI2CSI SE | `video-capture/hdmi2csi-se/` | 📋 PLACEHOLDER | 占位目录 |
| HDMI2CSI FPC | `video-capture/hdmi2csi-fpc/` | ✅ ACTIVE | FPC 连接线设计 |
| HDMI USB MS2109 | `video-capture/hdmi-usb-ms2109/` | ✅ ACTIVE | USB 采集卡方案 |
| 核心板 H616 | `coreboard/h616/` | 🚧 WIP | 未完成设计 |
| 全集成 ARM Linux | `coreboard/fullmodule-armlinux/` | 🧪 EXPERIMENTAL | 全集成方案探索 |
| 继电器模块 | `accessories/relay-module/` | ✅ ACTIVE | 电源/复位控制 |
