# Products
Technical product context — hardware components, software algorithms, storage architecture, and privacy design. The agent grounds all contract language in this file to ensure technical accuracy.

## Hardware
### Smart Companion (Model MC-110)
**Category:** Edge Interaction Unit  
**Key Components:**
- **Input Element (140):** Microphone array (4-channel beamforming), capacitive touch sensors, **Optical Sensor (Camera)**: OmniVision OV9282 global shutter CMOS for user position tracking (±2cm accuracy) and facial expression analysis (Claim 1, Claim 2).
- **Output Element (142):** Speaker (2W full-range), 3.5" e-ink display module (low-power status), **Actuatable Element (144)**: Maxon EC-i 40 brushless DC motor robotic head for animation component (±0.5° precision).
- **Peripheral Datastore (146):** 32GB eMMC flash, encrypted with AES-256, for temporary storage of active interaction plans, persona models, and reviewed memory cards.
**Supplier Dependencies:** 
- Optical Sensor Module: OmniVision Technologies (Requires NDA + IP Assignment on custom firmware for position-tracking algorithms).
- Actuator Components: Maxon Motor (Requires precision tolerances ±0.1mm for animation sync with conversation timing).
**Technical Constraints:** 
- Optical sensor must capture data at ≤50ms latency for real-time animation alignment (Spec [0076]).
- Peripheral datastore must support automatic erasure commands from Interaction Engine within 5 seconds of sync confirmation (Spec [0023]).
- Power consumption: ≤5W average during active interaction; ≤0.5W in standby.

### Link Device (Model LD-115)
**Category:** Secure Primary Datastore Hub  
**Key Components:**
- **Primary Datastore (116):** 256GB NVMe SSD with hardware encryption (Microchip ATECC608B secure element), centralized repository for long-term user data, memory card history, and persona model refinements.
- **Connectivity:** Personal Area Network (PAN) transceiver: Nordic Semiconductor nRF52840 (Bluetooth Low Energy 5.2 + IEEE 802.15.4) for proximity-based sync (Spec [0027]).
**Supplier Dependencies:** 
- Encrypted Storage Chip: Microchip Technology (Requires secure boot + tamper-detection capabilities).
- PAN Module: Nordic Semiconductor (Must support proximity-based triggers with RSSI threshold ≤-70dBm for ≤3m range).
**Technical Constraints:** 
- **No I/O Elements:** Device must lack screen, buttons, USB ports, audio jacks, or speakers to prevent direct user interaction (Spec [0022], [0025]).
- Access mediated exclusively via authenticated Smart Companions within PAN range; authentication via ECDSA P-256 key exchange.
- Physical enclosure: IP54-rated aluminum housing with tamper-evident seals.

## Software & Algorithms
### Interaction Engine (120)
**Description:** Central logic unit that generates interaction plans (conversation + animation) based on persona models and memory states. Processes multimodal inputs (optical, audio, touch) at ≤100ms end-to-end latency.  
**IP Status:** Proprietary Trade Secret / Patent Pending (PCT/IB2026/050123).  
**Licensing Relevance:** Core logic cannot be licensed out; API access only for certified partners. No reverse engineering permitted.

### Persona Model (150)
**Description:** Dynamic user profile comprising Relationship Stage, Personality, Mood, Biographical, and Wellness components (Spec [0038]). Updates in real-time using Bayesian inference on multimodal inputs.  
**IP Status:** Patent Pending (Claims 1, 3-4).  
**Licensing Relevance:** Data structure definitions are confidential; aggregated, anonymized insights may be shared with healthcare partners under DPA.

### Spaced Repetition Algorithm (DSR)
**Description:** Calculates Difficulty (D), Stability (S), and Retrievability (R) using 19 distinct parameters (Spec [0035]). Default parameters derived from analysis of 220M+ review logs (Ye et al. 2022 public dataset).  
**IP Status:** **High Risk / Mixed.** Core DSR concepts are public prior art (Ye et al. KDD 2022, FSRS). Specific integration with animation/persona + hybrid storage is Patent Pending.  
**Licensing Relevance:** Must ensure freedom-to-operate; avoid claiming ownership of base DSR math in contracts. Focus IP claims on the *integration* with hardware/storage architecture and real-time animation modulation.

## Storage Architecture
**Architecture Description:** 
- **Hybrid Model:** Temporary data resides on Smart Companion (Peripheral Datastore 146); long-term data resides on Link Device (Primary Datastore 116).
- **Sync Trigger:** Proximity-based PAN detection (BLE RSSI ≤-70dBm) (Spec [0023]).
- **Flow:** Peripheral → Primary (encrypted TLS 1.3) → Automatic Erasure of Peripheral (Spec [0080]).
**Patent Status:** **Core Protected Asset.** Patent Pending (PCT/IB2026/050123, Claims 1, 7, 8).
**Privacy Design:**
- **Automatic data erasure:** Triggered upon successful sync confirmation signal from Primary Datastore; erases reviewed memory cards, learning states, and temporary persona inputs within 5 seconds (Spec [0023]).
- **Data residency:** Primary datastore physically isolated on Link Device (no I/O) to prevent unauthorized access; all data encrypted at rest (AES-256) and in transit (Spec [0025]).
- **Access controls:** Authenticated Smart Companions only (ECDSA P-256); encryption required for PAN transmission; audit logs for all access attempts (Spec [0030]).
**Contract Relevance:** Customer terms must accurately disclose the hybrid model and erasure behavior (including data loss risk if sync fails). Supplier agreements must not grant access to architecture details beyond what is necessary for component functionality.

## Privacy Safeguards Summary
| Safeguard | Description | Contract Disclosure Required |
| :--- | :--- | :--- |
| **Hybrid storage** | Data split between Companion (temp, ≤24h retention) and Link Device (permanent, encrypted) | Yes — customer terms, privacy policy |
| **Automatic data erasure** | Peripheral data wiped within 5s after PAN sync confirmation; user notified via LED indicator | Yes — customer terms, setup guide |
| **Data breach response** | 72-hour notification (GDPR); Liability capped at USD $250,000 per incident; exclude consequential damages | Yes — customer terms + DPAs |
| **No IP claim on user data** | Company does not own user-generated memory cards, facial data, or conversation history | Yes — customer terms, IP clause |
| **No I/O on Link Device** | Physical security constraint: LD-115 has no screen/buttons/ports; access via authenticated MC-110 only | Yes — technical exhibits, supplier specs |