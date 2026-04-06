# STM32F103 KVM Host

> 🚧 **开发中** — 占位目录

## 概述

基于 STM32F103 的低成本 KVM 主机方案。

### 特性规划
- STM32F103 原生 USB Device (Full Speed 12Mbps)
- USB HID 键盘 + 鼠标模拟
- 通过 SPI/UART 连接上位机或独立运行
- 成本极低 (F103 约 ¥3)

### 限制
- Full Speed USB 仅支持 12Mbps（够用：HID 报告极小）
- 无原生 High Speed USB，不能直接做 UVC 视频采集
- 需要外部以太网模块 (W5500/ENC28J60) 或依赖上位机网络

### 硬件
- MCU: STM32F103C8T6 (Blue Pill) 或 STM32F103RCT6
- USB: PA11 (D-) / PA12 (D+) → 被控主机
- 通信: UART/SPI → 上位机

### 开发栈
- PlatformIO + STM32Cube HAL 或 libopencm3
- USB Device Library: TinyUSB 或 stm32-usb
