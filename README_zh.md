# SimpleIPMI

**[English](README.md)** 

An [RCOS](https://rcos.io) Project

开源、低成本的 KVM-over-IP 解决方案。通过浏览器远程控制物理主机的键盘、鼠标、视频画面和电源开关，功能类似商用 IPMI/BMC 系统。

## 核心功能

- **远程视频** — HDMI 采集 (USB/CSI)，MJPEG 视频流
- **远程键鼠** — USB HID 键盘 + 鼠标模拟
- **电源控制** — 光耦/继电器隔离的开机、关机、重启
- **Web 管理面板** — 浏览器直接操控，零客户端安装
- **灵活接入** — WiFi AP 直连 / 有线局域网 / Tailscale 远程

## 系统架构

项目支持三种不同的主控架构：

### ARM Linux 主控（可用）

基于 ARM Linux SBC（CM4、OrangePi）的全功能 KVM 方案。SBC 运行 Python (FastAPI) 服务端，通过 USB 采集卡获取视频，通过 ESP32-S3 HID Bridge 或原生 USB OTG 控制目标机键鼠。

```
用户 (浏览器)
     │
     ▼
┌──────────────────────────┐
│  ARM Linux SBC           │
│  FastAPI 服务端           │
│  ┌────────┐ ┌──────────┐ │
│  │ 视频采集│ │ HID 管理 │ │
│  │(USB Cap)│ │(ESP32/OTG)│ │
│  └────┬───┘ └────┬─────┘ │
└───────┼──────────┼────────┘
        │          │
   HDMI 输入   USB HID 输出 ──→ 被控主机
```

### MCU 主控（开发中）

基于 ESP32-S3 或 STM32 的轻量级独立方案。MCU 直接处理 WiFi AP、Web 服务 (SPIFFS) 和 USB HID，无需 Linux，无需采集卡，成本最低，适用于单机管控。

### Composite 集中管理（开发中）

运行在 Ubuntu (x86/ARM) 上的中央管理服务器。同时管理多个 KVM Host 和 USB 采集卡，提供统一 Web 面板，实现多目标机的集中控制。

## 仓库结构

```
simpleipmi/
├── hosts/                            # 主控设备 (KVM Host 固件/软件)
│   ├── esphost-esp32s3/              #   ESP32-S3 MCU 方案 (WiFi AP + HID)
│   ├── armhost-cm4/                  #   CM4 ARM Linux 方案 (网络 + HID Bridge)
│   ├── armhost-orangepi4/            #   OrangePi CM4 方案 (USB OTG HID)
│   ├── stmhost-f103/                 #   STM32F103 MCU 方案 (开发中)
│   └── esphost-esp32c3(switch_only)/ #   ESP32-C3 纯开关方案 (开发中)
│
├── hardware/                         # 硬件设计文件 (原理图/PCB/BOM)
│   ├── km/                           #   键鼠模拟模块
│   ├── kvm-carrier/                  #   KVM 载板
│   ├── coreboard/                    #   核心板设计
│   └── accessories/                  #   配件 (视频采集/继电器等)
│
├── composite/                        # 多机集中管理系统 (开发中)
│   └── server/
│
├── shared/                           # 跨设备共享资源
│   └── protocol/                     #   通信协议定义 (protocol.h)
│
└── docs/                             # 文档资料
```

## Host 方案对比

| | ARM CM4 | OrangePi CM4 | ESP32-S3 | STM32F103 |
|---|---|---|---|---|
| **架构** | ARM Linux | ARM Linux | MCU | MCU |
| **成本** | 待定 | 待定 | 待定 | 待定 |
| **视频采集** | USB 采集卡 | USB 采集卡 | 需外接 | 无 |
| **键鼠 HID** | ESP32-S3 串口桥接 | 原生 USB OTG | 原生 USB OTG | 原生 USB |
| **网络** | 以太网/WiFi | 以太网/WiFi | WiFi AP | 需外接 |
| **Web 面板** | FastAPI 服务端 | FastAPI 服务端 | 内置 (SPIFFS) | 无 |
| **状态** | 可用 | 可用 | 开发中 | 开发中 |

## 快速开始

### ARM CM4 主控

**准备:** CM4 兼容 SBC + ESP32-S3 (HID Bridge) + USB 采集卡

```bash
# 在 CM4 上部署服务端
cd hosts/armhost-cm4/server
pip install -r requirements.txt
python main.py

# 烧录 ESP32-S3 HID Bridge 固件
cd hosts/armhost-cm4/firmware
pio run -t upload
```

详见 → [hosts/armhost-cm4/docs/DEVELOPMENT.md](hosts/armhost-cm4/docs/DEVELOPMENT.md)

## 硬件设计

所有 PCB/原理图设计文件在 `hardware/` 目录，按功能分类：

| 分类 | 说明 |
|------|------|
| `km/` | 键鼠模拟模块 (ESP32-S2, XIAO-ESP32S3, STM32F103) |
| `kvm-carrier/` | KVM 载板 (PCIe CM4 v1/v2, T113) |
| `coreboard/` | 核心板 (H616, ARM Linux 全集成) |
| `accessories/` | HDMI 采集 (Toshiba TC358743, MS2109)、继电器 |

详见 → [hardware/README.md](hardware/README.md)

## 开发路线

**已完成**
- ARM CM4 KVM Host + ESP32-S3 HID Bridge
- OrangePi CM4 KVM Host (原生 USB OTG)
- Web 管理面板 (仪表盘 + KVM + 终端)

**待完成**
- ESP32-S3 独立 MCU Host
- STM32F103 低成本 MCU Host
- Composite 多机管理系统
- H616 核心板

## 关于 RCOS

本项目在 [Rensselaer Center for Open Source](https://rcos.io) (RCOS) 下开发。RCOS 是 Rensselaer Polytechnic Institute 的学生开源组织，支持服务于公共利益的开源软件开发。

## License

MIT
