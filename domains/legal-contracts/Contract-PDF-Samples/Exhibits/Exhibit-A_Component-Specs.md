# EXHIBIT A: COMPONENT SPECIFICATIONS
**Agreement Reference:** Hardware Supplier Agreement No. HSA-2026-001-HK  
**Effective Date:** January 14, 2026  
**Parties:** Memora Technologies Limited ("Buyer") and Precision Components Ltd. ("Supplier")  

---

## 1. Optical Sensor Module (Model OS-2026)
**Purpose:** User position tracking and facial expression analysis for Smart Companion (Model MC-110).

### 1.1 Technical Specifications
| Parameter | Requirement | Tolerance |
| :--- | :--- | :--- |
| **Sensor Type** | Global Shutter CMOS | OmniVision OV9282 or equivalent |
| **Resolution** | 1280 x 800 pixels | ±5% |
| **Frame Rate** | 60 fps minimum | ≥60 fps |
| **Latency** | End-to-end processing for position tracking | ≤50 milliseconds |
| **Accuracy** | User position tracking | ±2 centimeters |
| **Accuracy** | Facial expression analysis confidence | ≥95% |
| **Interface** | MIPI CSI-2 | Compatible with MC-110 SoC |
| **Power Consumption** | Average operational power | ≤500 milliwatts |
| **Operating Temperature** | Ambient range | 0°C to 45°C |
| **Dimensions** | Module size | 10mm x 10mm x 5mm (max) |

### 1.2 Firmware Requirements
- **Custom Firmware:** Supplier shall embed Buyer's proprietary position-tracking algorithm (provided under NDA).
- **Security:** Secure boot required; no unauthorized debug ports accessible.
- **Data Output:** Raw optical data must be processed locally; only position vectors and expression tags transmitted to Main Processor.

### 1.3 Quality Standards
- **Defect Rate:** ≤500 PPM (Parts Per Million).
- **Testing:** 100% functional testing on latency and accuracy.
- **Certification:** RoHS, CE, FCC Part 15 compliant.

---

## 2. Link Device Enclosure (Model LD-115)
**Purpose:** Housing for Primary Datastore with strict security constraints.

### 2.1 Physical Specifications
| Parameter | Requirement | Notes |
| :--- | :--- | :--- |
| **Dimensions** | 100mm x 100mm x 30mm | ±1mm |
| **Material** | Aluminum Alloy | IP54 Rated (Dust/Water Resistant) |
| **Weight** | ≤250 grams | Including internal components |
| **Color** | Matte White (Pantone 11-0601) | Non-reflective finish |

### 2.2 ⚠️ Critical Security Constraints (No I/O)
**The Link Device Enclosure MUST NOT include any of the following elements:**
- [ ] **NO** External USB, HDMI, or Power Ports (Wireless charging only).
- [ ] **NO** Buttons, Switches, or Touch Interfaces.
- [ ] **NO** Screens, LEDs, or Visual Indicators (Except internal status light not visible externally).
- [ ] **NO** Speakers, Microphones, or Audio Jacks.
- [ ] **NO** Reset Pins accessible without proprietary tool.

**Access Mechanism:**
- Internal NVMe slot accessible **only** via Supplier-provided proprietary security tool (Model TOOL-LD-01).
- Tamper-evident seals required on all enclosure seams. Seal breakage voids warranty.

### 2.3 Antenna & Connectivity
- **Integrated Antenna:** Nordic nRF52840 compatible (2.4GHz BLE/IEEE 802.15.4).
- **Range:** Effective PAN range ≤3 meters (RSSI threshold ≤-70dBm).
- **Placement:** Internal antenna must not be obstructed by aluminum housing (use plastic window insert if necessary).

### 2.4 Quality Standards
- **Durability:** Drop test certified (1.0m onto concrete, 6 sides).
- **Tamper Evidence:** Seals must show visible "VOID" pattern if removed.
- **Certification:** ISO 9001:2015 manufacturing facility required.

---

## 3. Delivery & Packaging
- **Packaging:** Anti-static shielding bags for Optical Sensors; Protective foam for Enclosures.
- **Labeling:** Each unit must bear unique serial number QR code linked to Buyer's database.
- **Documentation:** Certificate of Compliance (CoC) required per batch.

**Approved By:**  
_Elena Rossi, CTO, Memora Technologies Limited_  
_Date: January 14, 2026_

**Acknowledged By:**  
_David Tan, Director of Sales, Precision Components Ltd._  
_Date: January 14, 2026_