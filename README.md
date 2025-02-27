# SimpleIPMI (Intelligent Platform Management Interface) Project Proposal

## Project Title:
SimpleIPMI (Intelligent Platform Management Interface)

A RCOS Project
## Project Contributors:
- **Yinxiang Zhao** (zhaoy24@rpi.edu)
- **Philip Peng** (pengz4@rpi.edu)

---

## Vision:
The vision of SimpleIPMI is to create an affordable remote management solution for personal computers and local servers, combining basic functionality with IoT and advanced features.

## Stack:
- **Hardware**: ESP32 microcontroller, ARM development boards.
- **Software**: Ubuntu ARM, IoT platforms (e.g., HomeKit, MiJia).
- **Tools**: Dupont wires, relays, PCB design tools, 3D printing.

---

## Background:
Over the last decade, PC performance has improved significantly, making high-performance systems affordable for most users. However, regular home computer accessories still lack remote access features. This forces users to invest in expensive workstations or servers for these capabilities, which is unnecessary for most personal use cases.

The open-source community already has a solution called **PiKVM**, which replicates many functions of BMC/IPMI. However, PiKVM requires a Raspberry Pi, which isn’t always practical for regular users. Software like **Microsoft Remote Desktop** is useful but limited to certain OS versions and doesn’t fully cover our objectives.

This project aims to create a budget-friendly device for personal computers and small local servers that provides basic remote access without costly setups.

---

## Project Proposal:
We’re building a **low-cost remote management device** using basic components. The first version will focus on the ESP32 microcontroller for essential functions, with plans to add advanced features using ARM-based boards later.

### Goals:
1. Develop a **basic remote management system** with ESP32 to handle tasks like remote restart, power-on, and LED indicators.
2. Integrate **IoT functionality** for compatibility with smart home systems.
3. Transition to **ARM development boards** for advanced features like video capture and input simulation.
4. Design a **professional final product** with proper PCB design and casing.

---

## Project Design:
### **Version 1 (ESP32)**
- Basic remote control features like **power on/off** and **LED indicators**.
- Built using simple wiring and relays.

### **Future Versions:**
1. Add **simulated mouse/keyboard inputs** and **video capture** with ARM-based boards.
2. Use **Ubuntu ARM** as the development platform for advanced features.
3. Replace DIY circuits with **PCB designs** and add **3D-printed protective casing**.

---

## Roadmap:

| Stage | Goals | Timeline |
|--------|-----------------|----------------------------------------------------------------------------------------|
|   Stage 1: ESP Basic     | Implement essential features like power on/off, restart, and LED indicators. | Month 1 |
|   Stage 2: SmartSwitch   | Integrate with IoT systems (HomeKit, MiJia) for smart home connectivity.     | Month 2 |
|   Stage 3: ARM Upgrade   | Switch to an ARM development board for video capture and input simulation.   | Month 3 |
|   Stage 4: Final Product | Replace soldering with PCB, refine hardware design with 3D printing.         | Month 4 |

---

## Summary:
SimpleIPMI is about building a **cost-effective solution** for remote PC and local server management. By using **low-cost hardware** and **simple tools**, we’re creating a useful product without excessive costs. With a clear roadmap and realistic goals, we’re confident in delivering this project within **four months**.
