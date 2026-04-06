# SI BMC — SimpleIPMI 基板管理控制器

**[English](README.md)**

开源、低成本的 KVM-over-IP 解决方案。通过浏览器远程控制物理主机的键盘、鼠标、视频画面和电源开关，功能类似商用 IPMI/BMC 系统。

支持多种硬件平台，从 ¥30 的 ESP32-S3 开发板到 CM4 级 ARM Linux SBC，覆盖单机管理到多机集中管控的场景。

## 核心功能

- **远程视频** — HDMI 采集 (USB/CSI)，MJPEG 视频流
- **远程键鼠** — USB HID 键盘 + 鼠标模拟
- **电源控制** — 光耦/继电器隔离的开机、关机、重启
- **Web 管理面板** — 浏览器直接操控，零客户端安装
- **灵活接入** — WiFi AP 直连 / 有线局域网 / Tailscale 远程

## 系统架构

```
                        ┌──────────────────────────────────┐
    用户 (浏览器) ──────→│         Web 管理面板              │
                        │   视频流 │ HID 输入 │ 电源控制     │
                        └────┬─────┴────┬─────┴────┬────────┘
                             │          │          │
                      ┌──────┴──────────┴──────────┴──────┐
                      │          KVM Host (主控)           │
                      │  ESP32-S3 / CM4 / OrangePi / ...   │
                      └──┬──────────┬──────────┬──────────┘
                         │          │          │
                    USB 采集卡   USB HID     GPIO 继电器
                    (HDMI输入)  (键鼠输出)   (电源控制)
                         │          │          │
                         └──────────┴──────────┘
                              被控主机 (Target)
```

## 仓库结构

```
simpleipmi/
├── hosts/                            # 主控设备 (KVM Host 固件/软件)
│   ├── esphost-esp32s3/              #   ESP32-S3 单片机方案 (WiFi AP + HID)
│   ├── armhost-cm4/                  #   CM4 ARM Linux 方案 (网络 + HID Bridge)
│   ├── armhost-orangepi4/            #   OrangePi CM4 方案 (USB OTG HID)
│   ├── stmhost-f103/                 #   STM32F103 低成本方案 (开发中)
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

| | ESP32-S3 | ARM CM4 | OrangePi CM4 | STM32F103 |
|---|---|---|---|---|
| **成本** | ~¥30 | ~¥200 | ~¥150 | ~¥15 |
| **视频采集** | 需外接 | USB 采集卡 | USB 采集卡 | 无 |
| **键鼠 HID** | 原生 USB OTG | ESP32-S3 串口桥接 | 原生 USB OTG | 原生 USB |
| **网络** | WiFi AP | 以太网/WiFi | 以太网/WiFi | 需外接 |
| **Web 面板** | 内置 SPIFFS | FastAPI 服务端 | FastAPI 服务端 | 无 |
| **适用场景** | 单机简易管控 | 功能完整的远程 KVM | 功能完整的远程 KVM | 超低成本 HID |
| **状态** | 可用 | 可用 | 可用 | 开发中 |

## 快速开始

### 方案一：ESP32-S3（最简单）

**准备:** ESP32-S3-DevKitC-1 开发板 + 杜邦线 + 光耦模块

```bash
# 安装 PlatformIO
pip install platformio

# 编译烧录固件
cd hosts/esphost-esp32s3/firmware
pio run -t upload

# 上传 Web 界面 (SPIFFS)
pio run -t uploadfs

# 连接 WiFi: SI-BMC-XXXX，打开 http://192.168.4.1
```

详见 → [hosts/esphost-esp32s3/README.md](hosts/esphost-esp32s3/README.md)

### 方案二：ARM CM4（功能完整）

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

- [x] ESP32-S3 单机 KVM Host
- [x] CM4 ARM Linux KVM Host + ESP32-S3 HID Bridge
- [x] OrangePi CM4 KVM Host (USB OTG)
- [x] Web 管理面板 (仪表盘 + KVM + 终端)
- [ ] STM32F103 低成本 HID Host
- [ ] Composite 多机管理系统
- [ ] H616 核心板完成

## License

MIT
