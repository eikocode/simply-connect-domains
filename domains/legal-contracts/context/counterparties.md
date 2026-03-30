# Counterparties
Supplier, customer, and partner profiles — including known risk flags, negotiation history, and relationship context.

## Suppliers

### Precision Components Ltd.
**Type:** Hardware supplier (Optical sensors, Link Device enclosures)  
**Components/Services:**
- Optical Sensor Module (Model OS-2026): OmniVision OV9282 global shutter CMOS
- Link Device Enclosure (Model LD-115): Aluminum IP54 housing with no I/O elements
- Custom firmware for secure boot and PAN-triggered sync

**Risk Flags:**
- ⚠️ IP Assignment: Requires explicit assignment clause for "No I/O" design improvements (compliance.md §IP Ownership Rule)
- ⚠️ Data Security: Supplier tests components with real optical data; requires DPA for biometric data handling
- ⚠️ Lead Time: 8-week lead time for Optical Sensors may impact Q3 2026 launch

**Negotiation History:**
- Jan 2026: Initial NDA signed; agreed to IP Assignment Form (Exhibit C) for all work product
- Feb 2026: Pricing negotiation: Tier 3 pricing ($45/unit for OS-2026) secured for 10k+ volume
- Mar 2026: Quality standards agreed: ≤500 PPM defect rate; 100% functional testing

**Notes:**
- Preferred supplier for MC-110/LD-115 hardware; exclusive for "No I/O" enclosure design for 24 months
- Contact: David Tan, Director of Sales (david.tan@precisioncomp.sg)

---

### Cognitive Algorithms Inc.
**Type:** Software vendor / IP Licensor  
**Components/Services:**
- Licensed IP: Adaptive Spaced Repetition Engine (ASRE) v3.1 (DSR model with 19 parameters)
- Technical support for integration with persona models and hybrid storage

**Risk Flags:**
- ⚠️ Field of Use: License limited to "cognitive support applications"; must explicitly include "elderly care" and "companion robotics" (compliance.md §Patent Strategy)
- ⚠️ Joint Ownership: Avoid clauses creating joint IP ownership; all improvements must be assigned to Memora
- ⚠️ Sublicensing: No sublicensing rights without Memora's prior written consent

**Negotiation History:**
- Dec 2025: Initial term sheet: 8% royalty, $50k minimum annual
- Jan 2026: Field of Use expanded to include elderly care after legal review
- Feb 2026: IP Assignment clause finalized: Licensee improvements solely owned by Memora

**Notes:**
- Critical IP partner for DSR algorithm; license required for MC-110 software stack
- Contact: Sarah Chen, Chief Licensing Officer (sarah.chen@cogalgo.com)

---

### CloudSecure Services Ltd.
**Type:** Service provider (Cloud backup, data processing)  
**Components/Services:**
- Secure cloud backup for Link Device Primary Datastores (LD-115)
- GDPR/HIPAA-compliant data processing; encryption at rest/in transit

**Risk Flags:**
- ⚠️ Breach Notification: Must notify within 24 hours (stricter than GDPR 72h) per compliance.md §Standing Flags
- ⚠️ Subprocessors: AWS EMEA, Datadog, SendGrid pre-approved; any new subprocessor requires written consent
- ⚠️ Data Residency: Primary backups in EU (Luxembourg); ensure PDPO cross-border transfer safeguards

**Negotiation History:**
- Jan 2026: DPA executed with 24-hour breach notification clause
- Feb 2026: Security audit completed; ISO 27001 certification verified
- Mar 2026: Pricing finalized: $0.02/GB/month for encrypted storage

**Notes:**
- Sole provider for cloud backup of LD-115 Primary Datastore; critical for disaster recovery
- Contact: Patrick O'Brien, Data Protection Officer (patrick.obrien@cloudsecure.ie)

---

## Customers

### CareFacility Partners Ltd.
**Type:** Enterprise (Elderly care facility operator)  
**Products Covered:**
- Memora Smart Companion (MC-110) + Link Device (LD-115) bundles
- Deployment: 50 units for Hong Kong facilities; pilot program Q3 2026

**Risk Flags:**
- ⚠️ Medical Claims: Customer may request "medical device" positioning; must maintain "Wellness/Companion" disclaimer (compliance.md §Other Obligations)
- ⚠️ Data Sharing: Customer requests aggregated insights for research; must anonymize and obtain user consent per GDPR
- ⚠️ Liability: Customer seeks uncapped liability for health outcomes; must enforce USD $100 cap per Terms of Service

**Negotiation History:**
- Jan 2026: Pilot agreement signed: 10 units for 3-month trial
- Feb 2026: Data sharing terms negotiated: Aggregated, anonymized insights only; explicit user consent required
- Mar 2026: Liability cap accepted after legal review; added mutual indemnification clause

**Notes:**
- Strategic pilot customer for elderly care vertical; success could lead to 500+ unit order
- Contact: Mary Wong, Director of Operations (mary.wong@carefacility.hk)

---

### SilverTech Distributors Inc.
**Type:** Distributor (Consumer electronics, Asia-Pacific)  
**Products Covered:**
- Memora Smart Companion (MC-110) standalone units
- Regional distribution rights for Hong Kong, Singapore, Malaysia

**Risk Flags:**
- ⚠️ Sublicensing: Distributor requests right to sublicense support services; must limit to "non-exclusive, non-transferable" license
- ⚠️ Brand Usage: Strict guidelines required for marketing materials; no medical claims permitted
- ⚠️ Inventory Risk: Distributor seeks return rights for unsold units; must limit to defective units only

**Negotiation History:**
- Feb 2026: Distribution agreement drafted; territorial rights defined
- Mar 2026: Marketing guidelines approved; brand usage training scheduled
- Apr 2026 (Projected): Final signing pending liability cap agreement

**Notes:**
- Key channel partner for APAC consumer launch; requires careful IP protection in distribution terms
- Contact: James Lim, Regional Director (james.lim@silvertech.sg)

---

## IP Licensees / Licensors

### OmniVision Technologies
**Relationship:** Licensor (Background IP for optical sensor firmware)  
**IP Covered:**
- Background IP: OV9282 sensor architecture, global shutter technology
- License granted: Perpetual, irrevocable, royalty-free license for use in MC-110 Optical Sensor Module

**Risk Flags:**
- ⚠️ Improvements: Any firmware improvements for position-tracking must be assigned to Memora (per Hardware Supplier Agreement)
- ⚠️ Scope: License limited to MC-110 integration; cannot be used for other products without new agreement

**Notes:**
- Critical technology partner; sensor performance directly impacts optical tracking accuracy (Claim 1, Claim 2)
- Contact: Legal Department (ip.licensing@ovt.com)

---

### Nordic Semiconductor ASA
**Relationship:** Licensor (PAN module firmware)  
**IP Covered:**
- Background IP: nRF52840 BLE/IEEE 802.15.4 stack, RSSI-based proximity detection
- License granted: Standard EULA for commercial use in LD-115 Link Device

**Risk Flags:**
- ⚠️ Proximity Logic: Custom RSSI threshold logic (≤-70dBm for ≤3m) developed by Memora; must be treated as Memora IP
- ⚠️ Security: Firmware must support secure boot and encrypted PAN transmission per compliance.md §Data Handling Rules

**Notes:**
- PAN module critical for sync trigger and automatic erasure (Claim 1, Claim 8); performance impacts user experience
- Contact: Partner Management (partners@nordicsemi.no)