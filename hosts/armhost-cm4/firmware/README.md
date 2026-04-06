# ESP32-S3 USB HID Bridge Firmware

ESP32-S3 固件，作为 ARM 主板与被控主机之间的 USB HID 桥接器。

## 工作原理

```
ARM 主板 (任意 CM4 核心板)
     │ UART (TX/RX, 115200 baud)
     ▼
  ESP32-S3
     │ Native USB (GPIO19 D- / GPIO20 D+)
     ▼
  被控主机 (识别为 USB 键盘 + 鼠标)
```

## 硬件接线

### 完整接线图（含 OTA 刷写支持）

```
CM4 核心板 (5V供电, 3.3V GPIO)          ESP32-S3 (独立 3.3V DCDC)
════════════════════════════          ═══════════════════════════

 ┌─ 数据通道 ────────────────────────────────────────────────┐
 │ UART TX ────[1kΩ]──────────────→  GPIO43 (RX)             │
 │ UART RX ←───[1kΩ]─────────────   GPIO44 (TX)             │
 └───────────────────────────────────────────────────────────┘

 ┌─ OTA 刷写控制 ────────────────────────────────────────────┐
 │                         ┌──→ ESP32 3.3V                   │
 │                      [10kΩ] (上拉,防浮空)                  │
 │ GPIO_A (EN_PIN) ────────┴──→  EN (CHIP_EN / RESET)        │
 │                                                            │
 │                         ┌──→ ESP32 3.3V                   │
 │                      [10kΩ] (上拉,防浮空)                  │
 │ GPIO_B (BOOT_PIN) ─────┴──→  GPIO0 (BOOT MODE)           │
 └───────────────────────────────────────────────────────────┘

 ┌─ 电源 ───────────────────────────────────────────────────┐
 │ GND ──────────────────────────→  GND  (必须共地!)         │
 └───────────────────────────────────────────────────────────┘

         12V / 5V 总电源线
              │
     ┌────────┴────────┐
     ▼                  ▼
 DC-DC → 5V         DC-DC → 3.3V
     │                  │
 CM4 核心板          ESP32-S3
 (SoC内部3.3V)       (3.3V 逻辑)
 GPIO = 3.3V ✅      GPIO = 3.3V ✅
```

### 引脚对照表

| CM4 核心板 | 电阻 | ESP32-S3 | 功能 |
|-----------|------|----------|------|
| UART TX | 1kΩ 串联 | GPIO43 (RX) | 串口数据 → ESP32 |
| UART RX | 1kΩ 串联 | GPIO44 (TX) | 串口数据 ← ESP32 |
| GPIO_A | — | EN (CHIP_EN) | OTA 复位控制 |
| GPIO_B | — | GPIO0 | OTA 启动模式控制 |
| GND | — | GND | 共地 (必需) |

### 被动元件清单

| 元件 | 数量 | 位置 | 作用 |
|------|------|------|------|
| 10kΩ 电阻 | 2 | EN → 3.3V, GPIO0 → 3.3V | 上拉防浮空 (CM4 未启动时保持 ESP32 正常运行) |
| 1kΩ 电阻 | 2 | UART TX/RX 线上串联 | 反灌保护 (CM4 未上电时限制 ESP32 TX 电流) |

### 电压兼容性说明

- 所有 CM4 标准核心板 (RK3566/RK3399/H616/BCM2711) 的 **GPIO 逻辑电平均为 3.3V**
- ESP32-S3 的 GPIO 逻辑电平也是 **3.3V**
- 即使 CM4 核心板由 5V 供电、ESP32 由独立 DCDC 供电，**不需要电平转换器**
- ⚠️ **必须共地**：两路 DCDC 必须共 GND，否则串口无参考基准

### 上电时序保护

| 场景 | EN 状态 | GPIO0 状态 | ESP32 行为 |
|------|---------|-----------|-----------|
| CM4 未上电 | 10kΩ 上拉到 HIGH | 10kΩ 上拉到 HIGH | 正常运行 ✅ |
| CM4 运行中 | ARM GPIO 控制 | ARM GPIO 控制 | 正常运行 ✅ |
| CM4 触发 OTA | 拉低→释放 | 先拉低再释放 | 进入 Download 模式 → 刷写 |

## OTA 固件刷写

ARM 主板可通过 Web API 上传 `.bin` 固件文件，自动刷写 ESP32-S3：

```
用户上传 .bin  →  POST /api/esp32/flash  →  ARM GPIO 控制进入 Download 模式
                                          →  esptool.py 串口刷写
                                          →  GPIO 复位 ESP32-S3
                                          →  自动恢复 HID 桥接
```

在 ARM 端安装 esptool:
```bash
pip install esptool
```

## 编译 & 烧录

需要安装 [PlatformIO](https://platformio.org/install):

```bash
# 安装 PlatformIO CLI
pip install platformio

# 编译
cd esp32s3_hid
pio run

# 首次烧录 (ESP32-S3 通过 USB 连接到开发机)
pio run --target upload

# 后续更新: 通过 Web 面板上传 .bin 即可 (OTA)
```

## 通信协议

详见 `include/protocol.h`。二进制帧格式：

```
[0xAA] [TYPE] [LEN] [PAYLOAD...] [CRC8]
```

| TYPE | 方向 | 说明 |
|------|------|------|
| 0x01 | Host→ESP32 | 键盘 HID 报告 (8 bytes) |
| 0x02 | Host→ESP32 | 鼠标 HID 报告 (7 bytes, 绝对定位) |
| 0x03 | Host→ESP32 | 心跳 Ping |
| 0x04 | Host→ESP32 | 释放所有键鼠 |
| 0x83 | ESP32→Host | 心跳回复 (含 USB 状态) |
| 0xFE | ESP32→Host | 错误报告 |

## LED 状态指示

- **慢闪 (1Hz)**：空闲等待
- **快闪**：正在接收键鼠数据
- **启动时闪 3 次**：初始化完成
