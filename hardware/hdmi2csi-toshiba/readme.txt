# HDMI to MIPI CSI-2 Module (TC358743XBG)

HDMI to MIPI CSI-2 module based on the Toshiba **TC358743XBG** bridge, connected to the baseboard using a **DF40C-40DS-0.4V** BTB connector and an FPC cable.

This document describes the hardware, main components, and integration notes for this board.

---

## 1. Key Features

- HDMI input via standard SMT HDMI connector (HDMI-001S)
- HDMI → MIPI CSI-2 conversion using **TC358743XBG**
- Board-to-board connector: **Hirose DF40C-40DS-0.4V(51)** (40-pin, 0.4 mm)
- MIPI CSI-2 and control lines routed through BTB and FPC
- On-board HDMI port interface/protection (TPD12S521)
- Local power generation from a single input rail (TLV62568 + TLV75725)
- 27 MHz reference crystal for the bridge device
- Small 2-layer/4-layer form factor (see PCB files)

---

## 2. Repository Contents

Typical directory layout (actual names may vary):

- `schematic/` – Schematic files for the HDMI2CSI module  
- `pcb/` – PCB layout and fabrication outputs  
- `bom/` – Full bill of materials (including this BOM)  
- `mechanical/` – STEP/DXF drawings and board outline  
- `doc/` – Datasheets, app notes, integration notes  
- `readme.txt` / `README.md` – This document  

---

## 3. Major Components (from BOM)

### 3.1 Active ICs

| RefDes       | Part Number      | Function (short)                         |
|--------------|------------------|------------------------------------------|
| U6           | TC358743XBG      | HDMI to MIPI CSI-2 bridge                |
| U1           | TPD12S521DBTR    | HDMI port interface/protection           |
| U7           | TLV62568ADRLR    | Step-down switching regulator            |
| U3           | TLV75725PDBVR    | Linear regulator                         |
| U2, U4       | BLM18EG221SN1D   | EMI/LC filter beads on supply lines      |
| X1           | OT2EL4C4JI-111OLP-27M | 27 MHz crystal for bridge clock    |

### 3.2 Connectors

| RefDes | Part Number           | Description                        |
|--------|-----------------------|------------------------------------|
| CN1    | DF40C-40DS-0.4V(51)   | 40-pin 0.4 mm BTB connector        |
| HDMI   | HDMI-001S             | SMT HDMI Type-A input connector   |

### 3.3 Inductors

| RefDes | Part Number     | Value |
|--------|-----------------|-------|
| L1     | WPN252012H1R0MT | 1 µH  |

(Used with U7 for the switching power stage.)

### 3.4 Capacitors (summary)

| Value   | Qty | Typical Use                          |
|---------|-----|--------------------------------------|
| 100 nF  | 22  | Local decoupling for all IC rails    |
| 1 µF    | 2   | Bulk decoupling / regulators         |
| 4.7 µF  | 1   | Regulator output/input buffering     |
| 10 µF   | 2   | Main input/output bulk capacitors    |
| 15 pF   | 2   | Crystal load capacitors              |
| 22 µF   | 1   | Additional bulk (bridge / HDMI rail) |

(Exact placements: see BOM and schematic.)

### 3.5 Resistors (summary)

| Description           | Value | RefDes (grouped)              |
|-----------------------|-------|------------------------------|
| Series / jumpers      | 0 Ω   | NOM, R14                     |
| Pull-up / bias        | 2 kΩ  | R1                           |
| Pull-up / bias        | 4.7 kΩ| R2, R3, R9, R10              |
| Pull-up / bias        | 10 kΩ | R11, R13                     |
| Divider / bias        | 27 kΩ | R12                          |
| Sense / bias          | 1 kΩ  | R15                          |
| Termination / bias    | 1.8 kΩ| R16, R17                     |
| High-value pull       | 100 kΩ| R18, R19                     |
| NC / test             | NC    | TST                          |

Exact usage (pull-ups, dividers, terminations) is visible in the schematic.

---

## 4. Power Architecture

High-level power path inferred from the BOM:

- Input supply from baseboard via **CN1**.  
- **U7 (TLV62568)** + **L1** + bulk capacitors generate a regulated intermediate rail.  
- **U3 (TLV75725)** generates a clean low-noise rail for the bridge / HDMI circuitry.  
- Multiple 100 nF and µF capacitors provide local decoupling on all IC rails.  
- Ferrite beads **U2, U4 (BLM18EG221SN1D)** isolate noisy domains and help with EMI.

Exact voltages, current budget, and sequencing must match the schematic and the target system.

---

## 5. Signal Overview

### 5.1 HDMI Side

- HDMI connector (HDMI-001S) routes TMDS, DDC, HPD, and power signals into **U1**.  
- **U1 (TPD12S521)** provides the HDMI port interface and protection before the signals reach the bridge.  
- ESD and surge robustness depend on U1 and layout around the HDMI connector.

### 5.2 Bridge and MIPI CSI-2

- **U6 (TC358743XBG)** receives HDMI signals and outputs MIPI CSI-2 lanes.  
- CSI-2 clock + data lanes are routed from U6 to **CN1** and then via BTB/FPC to the host.  
- I²C, reset, interrupt, and optional GPIO lines are also brought to **CN1** for control and status.

Check the schematic for:

- Lane count and mapping (CLK, D0…Dn)  
- Voltage levels (e.g. 1.2 V / 1.8 V I/O)  
- I²C addresses and pull-up locations

---

## 6. Baseboard / Host Interface

CN1 (DF40C-40DS-0.4V) carries:

- Power rails from the baseboard (input to U7 / U3 and any reference rails)  
- MIPI CSI-2 differential pairs to the SoC or adapter  
- I²C bus for configuring the bridge and HDMI interface IC  
- Reset / interrupt lines  
- Optional test or configuration pins as defined in the schematic

Always follow:

- Impedance and length matching rules for CSI-2 and any high-speed control lines  
- Connector mating orientation and pin numbering from the mechanical drawings  

---

## 7. Software and Integration Notes

Software is platform-dependent. Generic steps:

1. Add a device-tree (or equivalent) node for **TC358743XBG** connected on the I²C bus.  
2. Describe CSI-2 endpoints and routing from bridge to SoC camera interface.  
3. Configure regulators and power rails so the bridge and HDMI interface are powered before link bring-up.  
4. Use standard video tools (e.g. V4L2, GStreamer) to verify that CSI-2 frames are captured correctly.  

Additionally:

- The module cannot pass encrypted content unless your system and bridge configuration support it.  
- Supported resolutions and frame rates depend on the SoC’s CSI-2 receiver and the HDMI source.

---

## 8. Testing Checklist

Recommended bring-up sequence:

1. **Power check**  
   - Verify all rails from U7 and U3 are at expected voltage.  
   - Check current draw against design expectations.

2. **I²C check**  
   - Confirm that U6 (and any other I²C devices) acknowledge on the bus.

3. **HDMI detection**  
   - Connect a known-good HDMI source.  
   - Confirm HPD and DDC activity according to the bridge status registers.

4. **CSI-2 link**  
   - Enable the SoC CSI-2 receiver and check for clock and data activity.  
   - Validate that video frames are received with correct resolution and format.

5. **Long-run stability**  
   - Run continuously at target resolution to validate thermal and power margins.

Record any board-specific quirks or required register sequences under `doc/` for future reference.

---

## 9. License and Revision History

Fill these sections according to your project:

### License

- Hardware design license: e.g. CERN OHL, Apache-2.0, or another license of your choice.  
- Place the full license text at the repository root and reference it here.

### Revision History

| Rev | Date       | Description                           |
|-----|-----------|---------------------------------------|
| v1.0| YYYY-MM-DD | Initial release of HDMI2CSI module    |
| v1.1| YYYY-MM-DD | BOM updates / documentation cleanup   |


