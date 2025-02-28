# SimpleIPMI (Intelligent Platform Management Interface) Project Proposal

## Project Title:
SimpleIPMI (Intelligent Platform Management Interface)

## A RCOS Project
https://new.rcos.io/projects/simpleipmi/

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

## Roadmap:

| Stage | Goals | Timeline |
|--------|-----------------|------------------------------------------------------------------------------------------------|
|   Stage 1: ESP Basic     | Implement essential features like power on/off, restart, and LED indicators. |  🔄Progressing |
|                          |  ESP32 power on/off and LED status reading                                   |  ✅Completed   |
|                          |  Access to HA                                                                |  🔄Progressing |
|                          |  ESP32 OTG                                                                   |  🔄Progressing |
|   Stage 2: ARM Host      |  an ARM development board for video capture and KVM switch.                  |  📅Planned     |
|                          |  ARM host KVM                                                                |  📅Planned     |
|                          |  ARM host web management system                                              |  📅Planned     |
|   Stage 3: Final Product | Replace soldering with PCB, refine hardware design with 3D printing.         |  📅Planned     |

---

## Summary:
SimpleIPMI is about building a **cost-effective solution** for remote PC and local server management. By using **low-cost hardware** and **simple tools**, we’re creating a useful product without excessive costs. With a clear roadmap and realistic goals, we’re confident in delivering this project within **four months**.
