# Compliance & Regulatory
Regulatory obligations, patent strategy, IP ownership rules, and data handling requirements. The agent verifies every contract against this file before flagging or approving language.

## Regulatory Obligations
### GDPR (EU/UK)
**Applicability:** All Memora Smart Companion (MC-110) and Link Device (LD-115) units sold or operated in EU/UK regions; triggers due to biometric data processing (optical sensor facial recognition per Claim 2) and health-related wellness models (medication adherence, cognitive metrics).  
**Key Requirements:**
- Lawful basis for data processing: Explicit consent required for biometric data (optical sensor facial recognition); legitimate interest for service functionality.
- Data subject rights: Access, erasure ("right to be forgotten"), portability — *Aligned with automatic erasure feature*.
- Data processing agreements (DPAs) required with all processors (e.g., OmniVision for sensor firmware, Nordic for PAN module).
- Breach notification obligations: 72 hours to supervisory authority; affected users notified without undue delay.
**Contract Impact:** All customer-facing terms and supplier DPAs must reflect these requirements. Biometric consent must be separate opt-in with clear withdrawal mechanism.

### HIPAA (US)
**Applicability:** When Wellness Model (155) includes protected health information (PHI): medication adherence logs, treatment regimens, mobility metrics linked to identifiable US users.  
**Key Requirements:**
- Business Associate Agreements (BAAs) required with healthcare providers, care facilities, or cloud processors handling PHI.
- Minimum necessary data access principle: Link Device isolation supports this by limiting direct access.
- Breach notification within 60 days to HHS and affected individuals.
**Contract Impact:** Any contract involving PHI requires a compliant BAA. Data erasure logs must be auditable and retained for 6 years.

### Other Obligations
- **CCPA/CPRA (California):** Right to opt-out of data sales (not applicable—no data sales), but disclosure of data collection categories required.
- **PDPO (Hong Kong):** Data protection principles apply to all Hong Kong users; cross-border transfer restrictions.
- **FDA (US):** Current positioning is "Wellness/Companion" (non-medical device) to avoid 510(k). Contracts must not make medical claims (diagnose/treat/cure cognitive disease).
- **CE Marking (EU) / HKCA (Hong Kong):** Required for electronics safety + radio equipment (BLE/PAN).

## Patent Strategy
### Core Protected Assets
- **Hybrid Storage Architecture:** Peripheral (Smart Companion MC-110) → Primary (Link Device LD-115) → Automatic Erasure (Claims 1, 7, 8).
- **Link Device Design:** Lack of I/O elements (no screen/buttons/ports) for physical security (Spec [0022], [0025]).
- **Integration:** Animation component modulated by DSR Stability (S) values derived from optical sensor position data (Claim 1, Claim 5).

### Filed Patents
- **PCT Application:** PCT/IB2026/050123 (Filed: February 28, 2026; ISA: EPO).
- **US Provisional:** 63/456,789 (Filed: January 15, 2026).
- **Priority Claims:** Claims priority to US Provisional 63/456,789.

### IP Ownership Rule
- All IP created in connection with Memora products or using Memora resources is owned by **Memora Technologies Limited**, a company incorporated in Hong Kong.
- Contracts must not create exceptions to this. Employee/contractor agreements must include broad assignment clauses covering "adaptive interaction," "storage architecture," and "persona modeling" improvements.
- **Specific Constraint:** Supplier contracts for Optical Sensors or Link Devices must assign any improvements to the "No I/O" design or "PAN-triggered erasure" logic to Memora.

### Licensing Constraints
- **DSR Algorithm:** Base math is public (Ye et al. 2022). Do not claim exclusive ownership of "Spaced Repetition" generally. Claim specific *implementation* integrated with persona/storage/animation.
- **Open Source:** Audit all libraries (e.g., ROS 2 Humble, CesiumJS 1.105) for copyleft risks (GPL vs. MIT/Apache). Maintain SBOM.
- **Contract Impact:** Supplier and partner agreements must not transfer or cloud ownership of core IP (Storage Architecture). IP licensing deals must define scope precisely and exclude core architecture. No sublicensing without written consent.

## Data Handling Rules
### Hybrid Storage
- **Local (Peripheral - MC-110):** Temporary only. Contains active interaction plans, recent memory cards (≤24h retention), temporary persona inputs. Max retention: Until next PAN sync or 24 hours, whichever comes first.
- **Central (Primary - LD-115):** Long-term. Contains full history, persona refinements, audit logs. Resides on Link Device (No I/O). Encrypted at rest (AES-256).
- **Contract Disclosure:** Customer terms must explain that data is not stored permanently on the Companion robot; sync required for long-term retention.

### Automatic Data Erasure
- **Trigger:** Successful synchronization confirmation signal from Primary Datastore (Spec [0080]).
- **Scope:** Reviewed memory cards, learning states (D/S/R values), temporary persona inputs, optical sensor raw frames.
- **Timeline:** Within 5 seconds of sync confirmation; user notified via LED indicator on MC-110.
- **Contract Disclosure:** Must warn users that failing to sync within 24 hours may result in data loss (peripheral wipe pending sync).

### User Data IP
- Company does not claim IP ownership over user-generated data (memory cards, facial data, conversation history).
- Contracts must reflect this explicitly: "Memora receives a limited, non-exclusive license to use user data solely for service improvement and personalization."

### Data Breach Liability
- **Liability Cap:** Limited to direct damages up to **USD $250,000** per incident; exclude consequential damages (cognitive decline, health outcomes, lost profits).
- **Indemnification:** Company indemnifies for IP infringement; Customer indemnifies for misuse of health data or unauthorized sharing.

## Standing Flags
The agent must always flag the following clause types for review:
- [ ] **Data breach responsibility or indemnification without a liability cap** (Risk: Unlimited exposure for health data; violates compliance.md §Data Breach Liability).
- [ ] **IP ownership of user data claimed by the company or assigned to a counterparty** (Violates User Data IP Rule; compliance.md §User Data IP).
- [ ] **Sublicensing rights granted without explicit scope** (Risk: Core architecture leakage; violates Licensing Constraints).
- [ ] **Data retention or erasure terms that conflict with automatic erasure policies** (e.g., "Companion shall retain data for 1 year" contradicts Spec [0023] and compliance.md §Automatic Data Erasure).
- [ ] **Any clause that could cloud ownership of the core storage architecture patent** (e.g., Supplier claiming IP on "Link Device No I/O design" or "PAN-triggered erasure logic").
- [ ] **Medical Claims:** Any language suggesting the device diagnoses or treats cognitive disease (FDA risk; violates "Wellness/Companion" positioning).
- [ ] **Biometric Consent:** Missing explicit opt-in language for optical sensor facial recognition (GDPR/IL BIPA risk; violates GDPR §Key Requirements).
- [ ] **Breach Notification Timeline:** Any clause allowing >72 hours for GDPR breach notification or >60 days for HIPAA.