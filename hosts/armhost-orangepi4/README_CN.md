# SI BMC Server

**基于 Orange Pi CM4 (RK3566) 的带外管理控制器 (BMC / IP-KVM)**

> 通过网页远程控制目标主机 — 视频采集 + 键鼠模拟 + 电源管理，无需在目标机安装任何软件。

---

## 📋 目录

- [功能特性](#-功能特性)
- [系统架构](#-系统架构)
- [硬件准备](#-硬件准备)
- [接线说明](#-接线说明)
- [软件环境要求](#-软件环境要求)
- [快速开始](#-快速开始)
- [配置说明](#-配置说明)
- [使用指南](#-使用指南)
- [API 参考](#-api-参考)
- [故障排除](#-故障排除)
- [项目结构](#-项目结构)
- [扩展开发](#-扩展开发)

---

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| 🖥 **远程视频** | 通过 MS2109 USB 采集卡捕获目标机 HDMI 信号，MJPEG 实时推流到浏览器 |
| ⌨️ **键盘模拟** | USB OTG 模拟标准 USB 键盘，支持所有按键、修饰键、组合键 |
| 🖱 **鼠标模拟** | USB OTG 模拟绝对定位鼠标，精确点击目标机屏幕任意位置 |
| ⚡ **电源控制** | GPIO 控制开机 (短按)、强制关机 (长按 5s)、硬重启 |
| 🔋 **电源检测** | 通过 PCIe 12V 分压电路实时检测目标机电源状态 |
| 📊 **Dashboard** | 现代化仪表盘，实时显示 CPU、内存、温度、磁盘、网络等系统信息 |
| ⌨️ **软键盘** | 内置完整虚拟键盘，支持触屏设备和移动端操作 |
| 🔑 **快捷组合键** | 一键发送 Ctrl+Alt+Del、Alt+Tab、Alt+F4 等常用组合键 |
| 🔐 **认证保护** | 可选的 JWT Token 认证，保护管理接口安全 |
| 📱 **响应式设计** | 支持桌面端和移动端浏览器访问 |

---

## 🏗 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                     客户端浏览器                          │
│  ┌──────────────────┐  ┌─────────────────────────────┐   │
│  │   Dashboard 面板  │  │   KVM 远程桌面              │   │
│  │  · 系统监控       │  │  · MJPEG 视频流             │   │
│  │  · 电源控制       │  │  · 鼠标点击穿透             │   │
│  │  · 设备状态       │  │  · 物理键盘捕获             │   │
│  │  · GPIO 管理      │  │  · 虚拟软键盘               │   │
│  │  · 操作日志       │  │  · 组合键面板               │   │
│  └──────────────────┘  └─────────────────────────────┘   │
│            │ HTTP/WebSocket                               │
└────────────┼─────────────────────────────────────────────┘
             │
    ┌────────┴────────┐
    │  FastAPI Server  │ ← Orange Pi CM4 (RK3566)
    │    :8080         │
    ├──────────────────┤
    │ Video: V4L2/MJPEG│ ← MS2109 USB 采集卡 ← HDMI ← 目标机
    │ HID:  ConfigFS   │ ← USB OTG 线 → 目标机 USB 口
    │ GPIO: sysfs      │ ← 杜邦线 → ATX 电源/复位针脚
    └──────────────────┘
```

---

## 🔧 硬件准备

### 必需硬件

| 设备 | 型号/规格 | 说明 |
|------|-----------|------|
| 单板电脑 | **Orange Pi CM4** (RK3566) | 核心板 + 底板 |
| 视频采集卡 | **MS2109** 芯片 USB 采集卡 | HDMI 输入，USB 2.0 输出 |
| USB OTG 线 | USB-A / Type-C 数据线 | 连接 CM4 OTG 口到目标机 |
| HDMI 线 | 标准 HDMI 线 | 目标机 HDMI 输出到采集卡 |
| 杜邦线 | 母对母杜邦线 × 5 根 | GPIO 连接到目标机 ATX 针脚 |
| TF 卡 / eMMC | 16GB 以上 | 装载 Linux 系统 |
| 电源 | Type-C 5V/3A | CM4 供电 |

### 可选硬件

| 设备 | 说明 |
|------|------|
| 分压电阻 | 12V → 3.3V 分压检测电路 (PCIe 12V) |
| 光耦模块 | 隔离 GPIO 与 ATX 针脚（推荐用于生产环境） |

---

## 🔌 接线说明

### GPIO 引脚定义

| 功能 | GPIO 名称 | Linux GPIO 编号 | 方向 | 物理连接 |
|------|-----------|-----------------|------|----------|
| **电源控制** (PWR) | GPIO4_A6 | 134 | 输出 | → 目标机 ATX `Power SW+` |
| **复位控制** (RST) | GPIO1_A1 | 33 | 输出 | → 目标机 ATX `Reset SW+` |
| **12V 检测** | GPIO4_C0 | 144 | 输入 | ← PCIe 12V 分压电路输出 |

> **GPIO 编号计算公式**: `bank × 32 + group × 8 + pin`
> - GPIO4_A6 = 4×32 + 0×8 + 6 = **134**
> - GPIO1_A1 = 1×32 + 0×8 + 1 = **33**
> - GPIO4_C0 = 4×32 + 2×8 + 0 = **144**

### ATX 电源接线示意

```
Orange Pi CM4                     目标主机 ATX 针脚
──────────────                    ─────────────────
GPIO4_A6 (PIN ?) ─────────────── Power SW+ (开机)
GND              ─────────────── Power SW- (开机地)

GPIO1_A1 (PIN ?) ─────────────── Reset SW+ (复位)
GND              ─────────────── Reset SW- (复位地)

GPIO4_C0 (PIN ?) ←── 分压电路 ←── PCIe 12V (电源检测)
GND              ─────────────── PCIe GND
```

### 12V 分压电路

```
PCIe 12V ───┬─── [10kΩ] ───┬─── GPIO4_C0 (3.3V 安全输入)
             │               │
             └─── [3.3kΩ] ──┴─── GND

输出电压 = 12V × 3.3k / (10k + 3.3k) ≈ 2.98V (安全范围)
```

### USB 连接

```
目标主机                    Orange Pi CM4
────────                    ──────────────
HDMI 输出 ──── HDMI 线 ──── MS2109 采集卡 (USB 接 CM4 USB HOST)
USB 端口  ──── USB 线  ──── CM4 USB OTG 端口 (模拟键盘鼠标)
```

---

## 📦 软件环境要求

### Orange Pi CM4 系统要求

- **操作系统**: Ubuntu 20.04/22.04 或 Debian 11/12 (推荐 Ubuntu 22.04 Server)
- **Python**: 3.8+
- **内核要求**:
  - `CONFIG_USB_CONFIGFS=y` (USB ConfigFS 支持)
  - `CONFIG_USB_CONFIGFS_F_HID=y` (HID Gadget 功能)
  - `CONFIG_USB_GADGET=y`
  - UVC 摄像头支持 (MS2109 为 UVC 标准设备)

---

## 🚀 快速开始

### 方法一：一键安装 (推荐)

```bash
# 1. 将项目文件传输到 Orange Pi CM4
scp -r SI_server/ orangepi@<CM4_IP>:~/

# 2. SSH 登录 CM4
ssh orangepi@<CM4_IP>

# 3. 运行安装脚本
cd ~/SI_server
sudo bash scripts/install.sh

# 4. 启动服务
sudo systemctl start si_bmc

# 5. 在浏览器中访问
# http://<CM4_IP>:8080
```

### 方法二：手动安装

```bash
# ── 1. 安装系统依赖 ──────────────────────────────────────────
sudo apt update
sudo apt install -y python3 python3-pip v4l-utils libgpiod-dev gpiod

# ── 2. 安装 Python 依赖 ─────────────────────────────────────
cd ~/SI_server
pip3 install -r requirements.txt

# ── 3. 初始化 USB HID Gadget ────────────────────────────────
#    (必须以 root 运行，将 CM4 模拟为 USB 键盘+鼠标)
sudo bash setup_gadget.sh setup

# 验证 HID 设备是否创建成功
ls -la /dev/hidg*
# 应显示: /dev/hidg0 (键盘) 和 /dev/hidg1 (鼠标)

# ── 4. 启动服务 ─────────────────────────────────────────────
sudo python3 main.py

# 或在后台运行:
sudo python3 main.py &

# ── 5. 设置开机自启 (可选) ───────────────────────────────────
sudo cp si_bmc.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable si_bmc
sudo systemctl start si_bmc
```

### 验证安装

```bash
# 检查服务状态
sudo systemctl status si_bmc

# 检查 USB Gadget 状态
sudo bash setup_gadget.sh status

# 检查视频设备
v4l2-ctl --device=/dev/video0 --all

# 检查 API 是否响应
curl http://localhost:8080/api/status
```

---

## ⚙️ 配置说明

所有配置集中在 `config.yaml` 文件中：

```yaml
# 服务器设置
server:
  host: "0.0.0.0"    # 监听地址
  port: 8080          # 端口号

# 视频采集 (MS2109)
video:
  device: "/dev/video0"    # V4L2 设备路径
  width: 1920              # 目标分辨率
  height: 1080
  fps: 30                  # 目标帧率
  jpeg_quality: 85         # MJPEG 画质 (1-100)

# USB HID 设备
hid:
  keyboard_device: "/dev/hidg0"
  mouse_device: "/dev/hidg1"
  target_width: 1920       # 目标机屏幕分辨率
  target_height: 1080

# GPIO 引脚 (根据实际接线修改)
gpio:
  power:
    linux_gpio: 134        # GPIO4_A6
    short_press_ms: 500    # 短按开机
    long_press_ms: 5000    # 长按强制关机
  reset:
    linux_gpio: 33         # GPIO1_A1
    pulse_ms: 200          # 复位脉冲
  power_status:
    linux_gpio: 144        # GPIO4_C0 (12V 检测)

# 认证 (生产环境请启用并修改密码)
auth:
  enabled: false
  default_user: "admin"
  default_password: "admin"
```

---

## 📖 使用指南

### Dashboard 仪表盘

访问 `http://<CM4_IP>:8080` 进入仪表盘：

- **系统监控**: 实时 CPU/内存/温度/磁盘使用率（环形图）
- **电源控制**: 查看 12V 状态，一键开机/关机/重启（含确认弹窗）
- **设备状态**: 采集卡、HID 键盘鼠标的连接状态
- **GPIO 信息**: 当前 GPIO 引脚配置
- **KVM 预览**: 小窗实时预览目标机画面，点击进入全屏 KVM
- **操作日志**: 所有操作记录滚动显示

### KVM 远程桌面

访问 `http://<CM4_IP>:8080/kvm` 进入远程桌面：

**鼠标操作**:
- 在视频画面上 **直接点击** 即可操作目标机
- 支持左键、右键、中键
- 支持滚轮滚动
- 绝对定位模式，点哪指哪

**键盘操作**:
- 点击视频区域使其获得焦点，然后 **直接使用物理键盘** 输入
- 所有按键事件将被拦截并转发到目标机

**虚拟软键盘**:
- 点击工具栏 `⌨️ 软键盘` 按钮打开
- 完整 QWERTY 布局 + 功能键行
- Shift/Ctrl/Alt 等修饰键支持粘滞切换
- 适合触屏设备和移动端

**快捷组合键**:
- `C+A+Del` → Ctrl+Alt+Delete (打开任务管理器/登录)
- `Alt+Tab` → 切换窗口
- `Alt+F4` → 关闭窗口
- `Win` → 打开开始菜单
- `TTY1` → Ctrl+Alt+F1 (切换到终端)
- `GUI` → Ctrl+Alt+F7 (切换回桌面)
- `PrtSc` → 截屏

**画质调节**:
- 工具栏滑块调整 MJPEG 压缩质量 (10-100)
- 低画质 = 低带宽，高画质 = 高清晰度

**全屏模式**:
- 点击 `⛶ 全屏` 按钮进入全屏

---

## 🔗 API 参考

所有 API 路径前缀为 `http://<CM4_IP>:8080`

### 视频

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/stream` | MJPEG 视频流 (浏览器直接显示) |
| `GET` | `/api/snapshot` | 获取单帧 JPEG 截图 |
| `GET` | `/api/video/status` | 视频采集状态 |
| `POST` | `/api/video/quality?quality=85` | 设置画质 |

### HID (WebSocket)

| 协议 | 路径 | 描述 |
|------|------|------|
| `WS` | `/api/ws/hid` | WebSocket HID 输入通道 |

WebSocket 消息格式:
```json
// 键盘按下
{"type": "keydown", "code": "KeyA"}

// 键盘释放
{"type": "keyup", "code": "KeyA"}

// 鼠标移动 (x, y 为 0.0-1.0 的屏幕百分比)
{"type": "mousemove", "x": 0.5, "y": 0.3}

// 鼠标按下 (button: 0=左, 1=中, 2=右)
{"type": "mousedown", "x": 0.5, "y": 0.3, "button": 0}

// 鼠标释放
{"type": "mouseup", "x": 0.5, "y": 0.3, "button": 0}

// 滚轮
{"type": "wheel", "x": 0.5, "y": 0.3, "deltaY": -1}

// 组合键
{"type": "combo", "modifiers": ["ControlLeft", "AltLeft"], "keys": ["Delete"]}
```

### 电源控制

| 方法 | 路径 | 描述 |
|------|------|------|
| `POST` | `/api/power/on` | 短按电源键开机 |
| `POST` | `/api/power/off` | 长按电源键强制关机 |
| `POST` | `/api/power/reset` | 按复位键重启 |
| `GET` | `/api/power/status` | 读取 12V 电源状态 |

### GPIO

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/gpio/status` | GPIO 总状态 |
| `GET` | `/api/gpio/config` | GPIO 配置信息 |
| `POST` | `/api/gpio/custom/{name}?value=1` | 设置自定义 GPIO |
| `GET` | `/api/gpio/custom/{name}` | 读取自定义 GPIO |

### 系统信息

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/system/info` | CPU/内存/温度/磁盘/网络 |
| `GET` | `/api/system/logs?n=50` | 最近操作日志 |
| `GET` | `/api/status` | 全局状态总览 |

---

## 🔍 故障排除

### 视频采集卡未识别

```bash
# 检查 USB 设备
lsusb | grep -i "534d\|macro\|2109"

# 检查 V4L2 设备
v4l2-ctl --list-devices

# 如果 /dev/video0 不存在，尝试重新插拔采集卡
# 如果被识别为音频设备，需要添加 udev 规则
```

### USB HID Gadget 创建失败

```bash
# 检查内核是否支持 ConfigFS
ls /sys/kernel/config/

# 手动加载模块
sudo modprobe libcomposite

# 检查 UDC 控制器
ls /sys/class/udc/

# 如果没有 UDC，可能需要修改设备树
# 确保 USB OTG 端口的 dr_mode 设置为 "peripheral" 或 "otg"
```

### GPIO 权限问题

```bash
# 确保以 root 运行
sudo python3 main.py

# 或添加当前用户到 gpio 组
sudo usermod -aG gpio $USER
```

### 画面黑屏或卡顿

```bash
# 尝试降低分辨率和帧率
# 修改 config.yaml:
# video:
#   width: 1280
#   height: 720
#   fps: 15

# 检查 USB 带宽 (MS2109 需要 USB 2.0 以上)
lsusb -t
```

---

## 📁 项目结构

```
SI_server/
├── config.yaml              # 全局配置文件
├── main.py                  # FastAPI 主入口 (所有 API 路由)
├── requirements.txt         # Python 依赖
├── setup_gadget.sh          # USB OTG HID Gadget 初始化脚本
├── si_bmc.service           # systemd 服务单元文件
├── GPIOdefine               # GPIO 引脚定义 (原始文件)
│
├── modules/                 # 后端模块
│   ├── video.py             # V4L2 视频采集 + MJPEG 流
│   ├── hid.py               # USB HID 键盘/鼠标模拟
│   ├── gpio_ctrl.py         # GPIO 电源控制 (sysfs)
│   ├── system_info.py       # 系统信息采集 (psutil)
│   └── auth.py              # JWT 认证
│
├── static/                  # 前端
│   ├── index.html           # Dashboard 仪表盘
│   ├── kvm.html             # KVM 远程桌面
│   ├── css/
│   │   ├── main.css         # 设计系统 (暗色主题+毛玻璃)
│   │   ├── dashboard.css    # Dashboard 样式
│   │   └── kvm.css          # KVM 样式 (虚拟键盘等)
│   ├── js/
│   │   ├── api.js           # API 通信 + Toast + 确认框
│   │   ├── app.js           # Dashboard 逻辑
│   │   ├── kvm.js           # KVM 核心 (视频+输入)
│   │   ├── keyboard.js      # 虚拟键盘
│   │   └── mouse.js         # 鼠标坐标映射
│   └── assets/
│       └── favicon.svg      # 网站图标
│
└── scripts/
    └── install.sh           # 一键安装脚本
```

---

## 🔧 扩展开发

### 添加自定义 GPIO

在 `config.yaml` 中的 `gpio` 段添加：

```yaml
gpio:
  custom_gpios:
    - name: "led_status"
      linux_gpio: 150
      direction: "out"
      active_low: false
    - name: "buzzer"
      linux_gpio: 151
      direction: "out"
```

通过 API 控制：
```bash
# 设置值
curl -X POST "http://<IP>:8080/api/gpio/custom/led_status?value=1"

# 读取值
curl "http://<IP>:8080/api/gpio/custom/led_status"
```

### 添加新的 API 端点

在 `main.py` 中添加新路由即可：

```python
@app.get("/api/my-feature")
async def my_feature():
    return {"hello": "world"}
```

### 修改虚拟键盘布局

编辑 `static/js/keyboard.js` 中的 `layout` 对象即可自定义键盘布局。

---

## 📄 许可证

本项目仅供学习和内部使用。

---

*SI BMC Server v1.0 — Built for Orange Pi CM4 (RK3566)*
