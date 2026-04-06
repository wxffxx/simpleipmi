# SI BMC — ESP32-S3 轻量级基板管理控制器

基于 ESP32-S3-DevKitC-1 开发板的轻量级远程管理控制器。
通过 WiFi 热点提供 Web 管理界面，并通过原生 USB (OTG) 接口模拟 HID 键盘和鼠标来控制目标主机。

## 功能

- **Web 管理仪表盘** — 查看系统状态、电源控制、日志流
- **USB HID 键盘** — 通过网页捕获键盘输入，发送到目标主机
- **USB HID 鼠标** — 触摸板式相对鼠标控制
- **远程电源控制** — 通过光耦隔离控制目标主机电源/复位按钮
- **WiFi AP 模式** — 无需路由器，直接连接控制

## 硬件需求

| 组件 | 说明 |
|------|------|
| **开发板** | ESP32-S3-DevKitC-1 (N8R2/N8R8) |
| **OTG USB** | GPIO19(D-) / GPIO20(D+) — 连接到目标主机 USB 口 |
| **UART0** | GPIO43(TX) / GPIO44(RX) — 可选，调试串口 |
| **电源按钮** | GPIO4 — 光耦 — 目标主机 PWR_BTN |
| **复位按钮** | GPIO5 — 光耦 — 目标主机 RST_BTN |
| **电源状态** | GPIO6 — 目标主机 PWR_LED (检测开机状态) |
| **状态 LED** | GPIO48 (板载) |

### USB 接口说明

开发板上有两个 USB 口：

```
+----------------------------------+
|  ESP32-S3-DevKitC-1              |
|                                  |
|  [USB]  <- OTG (GPIO19/20)      |  -> 连接到【目标主机】
|  [COM]  <- USB-JTAG/Serial      |  -> 连接到【开发电脑】(仅烧录/调试用)
|                                  |
+----------------------------------+
```

## 快速开始

### 1. 环境准备

```bash
pip install platformio
cd SI_server/esp32s3_bmc
```

### 2. 烧录固件

进入下载模式：**按住 BOOT -> 短按 RST -> 松开 BOOT**

```bash
# 一键编译 + 烧录固件 + SPIFFS
./flash.sh all

# 或分步操作：
pio run                          # 编译固件
pio run --target buildfs         # 编译 SPIFFS 文件系统

# 使用 esptool 烧录 (通过 OTG 口)
esptool --chip esp32s3 --port /dev/cu.usbmodem21201 \
  --baud 460800 write-flash \
  --flash-mode dio --flash-size 8MB \
  0x10000 .pio/build/esp32s3/firmware.bin \
  0x670000 .pio/build/esp32s3/spiffs.bin
```

烧录完成后按 **RST** 按钮重启。

### 3. 连接使用

1. 将 OTG USB 口连接到目标主机
2. 手机/电脑连接 WiFi: **`SI-BMC`** (密码: `12345678`)
3. 打开浏览器访问: **`http://192.168.4.1`**
4. 登录密码: `admin`

## 项目结构

```
esp32s3_bmc/
├── platformio.ini          # PlatformIO 构建配置
├── flash.sh                # 一键编译烧录脚本
├── README.md               # 英文文档
├── README_CN.md            # 中文文档 (本文件)
├── src/
│   ├── config.h            # 全局配置 (引脚定义、WiFi、认证)
│   ├── main.cpp            # 入口：启动序列 + 主循环
│   ├── usb_hid.h/cpp       # USB HID 键盘 + 鼠标驱动
│   ├── gpio_ctrl.h/cpp     # GPIO 控制 (电源/复位/状态LED)
│   ├── network.h/cpp       # WiFi AP 网络管理
│   └── web_server.h/cpp    # Web 服务器 + WebSocket + REST API
├── data/                   # SPIFFS 静态资源 (Web UI)
│   ├── index.html(.gz)     # 仪表盘页面
│   ├── hid.html(.gz)       # HID 键鼠控制页面
│   ├── css/                # 样式文件
│   └── js/                 # 前端逻辑
│       ├── app.js          # 公共功能 (认证、Toast、API)
│       └── hid.js          # HID 控制 (WebSocket + 触摸板 + 键盘)
```

## 模块说明

### USB HID (`usb_hid.h/cpp`)

使用 ESP32-S3 原生 USB (TinyUSB) 模拟 HID 复合设备：

- **键盘**: 使用内置 `USBHIDKeyboard` 类，支持完整的 JavaScript `event.code` 到 USB HID 键码映射
- **鼠标**: 使用内置 `USBHIDMouse` 类（相对移动模式），前端触摸板发送 `dx/dy` 增量

> 注意: 绝对鼠标模式（自定义 HID 描述符）在当前 ESP32 Arduino 版本下与键盘复合设备冲突，
> 因此采用相对鼠标方案。

### Web 服务器 (`web_server.h/cpp`)

基于 ESPAsyncWebServer：

- **静态资源**: 从 SPIFFS 提供 gzip 压缩的 HTML/CSS/JS
- **REST API**: `/api/status`, `/api/power`, `/api/reset`, `/api/led`
- **WebSocket**: `/ws/hid` — 实时接收键盘/鼠标指令

### 网络 (`network.h/cpp`)

WiFi AP 模式：

- SSID: `SI-BMC`, 密码: `12345678` (可在 `config.h` 修改)
- IP: `192.168.4.1`
- 无需外部路由器，直连控制

## 关键配置

编辑 `src/config.h` 修改：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `AP_SSID` | `"SI-BMC"` | WiFi 热点名称 |
| `AP_PASSWORD` | `"12345678"` | WiFi 密码 |
| `AUTH_PASSWORD` | `"admin"` | Web 登录密码 |
| `PIN_PWR_BTN` | `4` | 电源按钮 GPIO |
| `PIN_RST_BTN` | `5` | 复位按钮 GPIO |
| `PIN_PWR_LED` | `6` | 电源状态检测 GPIO |

## 构建标志

```ini
build_flags =
    -DARDUINO_USB_MODE=0          # 原生 USB (非 JTAG)，启用 HID
    -DARDUINO_USB_CDC_ON_BOOT=0   # 不在 USB 口输出串口日志
    -DBOARD_HAS_PSRAM=0           # 禁用 PSRAM (节省启动时间)
```

> 注意: `USB_MODE=0` 后 USB 口不再输出串口日志，调试需要外接 USB-TTL 适配器到 UART0 引脚 (GPIO43/44)。

## 开发注意事项

1. **烧录方式**: 必须通过 COM 口（USB-JTAG）进入下载模式烧录，OTG 口用于 HID 输出
2. **前端修改**: 修改 `data/` 下的文件后要重新 gzip 并 `buildfs`
3. **重启**: 烧录后需手动按 RST，或通过 COM 口 RTS 信号自动复位

## License

Internal project — SI Server Team
