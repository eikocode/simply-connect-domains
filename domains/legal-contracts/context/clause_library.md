# Clause Library
Approved clause language, flagged patterns to avoid, and corrections captured from prior sessions. The agent consults this file before generating new language and appends corrections here when instructed.

---

## Supplier Agreements

### Approved Clauses

#### IP Assignment (Work Product)
> *"All inventions, designs, improvements, or works of authorship created by Supplier in connection with this Agreement—including modifications to the secure link device architecture (including designs that eliminate user-accessible I/O elements) or proximity-triggered data synchronization logic—shall be solely owned by Buyer. Supplier hereby assigns to Buyer all right, title, and interest in such Work Product."*

**✅ Compliance Check:**
- [x] Assigns all IP to Company (compliance.md §IP Ownership Rule)
- [x] Specifically mentions core protected assets (link device No I/O design, PAN sync logic)
- [x] No joint ownership language

#### Liability Cap (Supplier-Favorable)
> *"Except for breaches of confidentiality, intellectual property infringement, or gross negligence, Supplier's total aggregate liability under this Agreement shall not exceed USD $500,000 or twelve (12) months of fees paid under this Agreement, whichever is less. Neither party shall be liable for indirect, incidental, special, or consequential damages, including loss of profits or data."*

**✅ Compliance Check:**
- [x] Includes liability cap (compliance.md §Data Breach Liability)
- [x] Excludes consequential damages
- [x] Carve-outs for IP/Confidentiality/gross negligence

#### No I/O Specification (Technical Exhibit)
> *"Link Device (Model LD-115) shall be designed without input or output elements (no screen, buttons, USB ports, audio jacks, or speakers). Access to Primary Datastore is mediated exclusively via authenticated Smart Companions within PAN range (≤3 meters, RSSI ≤-70dBm). Tamper-evident seals required on all enclosure seams."*

**✅ Compliance Check:**
- [x] Enforces core patent feature (products.md §Link Device)
- [x] Specifies security constraints (No I/O, PAN range, tamper evidence)

---

### Flagged Patterns

#### Uncapped Liability
> *"Supplier shall be liable for all damages arising from use of components, including consequential, indirect, and punitive damages. There is no limit on Supplier's total liability."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Data Breach Liability (Liability Cap)
- **Risk:** Unlimited exposure for health data breaches; violates standing flag
- **Fix:** Add cap (e.g., USD $500,000) and exclude consequential damages

#### Vague IP Assignment
> *"Supplier assigns to Buyer any IP created specifically for Buyer's products."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §IP Ownership Rule (must be broad and explicit)
- **Risk:** "Specifically for" is ambiguous; may exclude improvements to core architecture
- **Fix:** Use approved language covering "modifications to secure link device architecture" etc.

#### Overly Broad Sublicensing
> *"Supplier may engage subprocessors to fulfill its obligations under this Agreement."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Standing Flags (Sublicensing Rights)
- **Risk:** Core architecture leakage via unvetted subprocessors
- **Fix:** Require prior written consent + impose same confidentiality obligations

---

### Corrections (Captured from Sessions)

| Date | Original Clause | Issue | Corrected Language |
| :--- | :--- | :--- | :--- |
| Jan 28, 2026 | "Supplier retains rights to improvements on background IP." | Clouds ownership of core IP | "Supplier retains ownership of pre-existing Background IP. Any improvements to Buyer's architecture (including No I/O design) are assigned to Buyer." |
| Feb 1, 2026 | "Liability capped at fees paid." | Too low for health data risk | "Liability capped at USD $500,000 or 12 months fees, whichever is less." |

---

## IP Licensing

### Approved Clauses

#### Field of Use (Elderly Care Inclusion)
> *"License is granted solely for use in cognitive support applications for elderly individuals, including memory training, personalized interaction, wellness monitoring, and companion robotics using smart companion hardware (Model MC-110) and link devices (Model LD-115)."*

**✅ Compliance Check:**
- [x] Explicitly includes "elderly care" and "companion robotics" (compliance.md §Patent Strategy)
- [x] Tied to specific product models for clarity

#### Licensee Improvements Ownership
> *"Any improvements, modifications, or integrations created by Licensee—including integration of the Licensed IP with optical sensor position tracking, persona models, or hybrid storage systems—shall be solely owned by Licensee."*

**✅ Compliance Check:**
- [x] Assigns improvements to Memora (compliance.md §IP Ownership Rule)
- [x] Specifically mentions core integrations (optical tracking, persona, storage)

#### No Joint Ownership
> *"The parties expressly agree that no joint ownership of intellectual property shall arise under this Agreement. All IP created by either party shall be owned solely by the creating party, except as expressly assigned herein."*

**✅ Compliance Check:**
- [x] Prohibits joint ownership (compliance.md §Standing Flags)
- [x] Clear assignment mechanism

---

### Flagged Patterns

#### Restrictive Field of Use
> *"License limited to educational applications. Use in healthcare, elderly care, or companion robotics requires separate written consent."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Patent Strategy (blocks core business model)
- **Risk:** Prevents deployment in target market (elderly companion)
- **Fix:** Expand Field of Use to explicitly include elderly care/companion robotics

#### Joint Improvement Ownership
> *"Any derivatives or enhancements to the Licensed Algorithm shall be jointly owned by Licensor and Licensee."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §IP Ownership Rule (all IP owned by Company)
- **Risk:** Clouds ownership of core integration patents (DSR + Animation + Storage)
- **Fix:** Assign all improvements solely to Licensee (Memora)

#### Unlimited Sublicensing
> *"Licensee may sublicense the Licensed IP to affiliates without prior consent."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Licensing Constraints (no sublicensing without consent)
- **Risk:** Core algorithm leakage to unvetted third parties
- **Fix:** Require prior written consent for any sublicense

---

### Corrections (Captured from Sessions)

| Date | Original Clause | Issue | Corrected Language |
| :--- | :--- | :--- | :--- |
| Jan 28, 2026 | "Field of Use: Educational applications only." | Excludes elderly care target market | Expanded to include "elderly care, companion robotics, wellness monitoring" |
| Feb 1, 2026 | "Improvements jointly owned." | Violates IP Ownership Rule | Changed to "Improvements solely owned by Licensee (Memora)" |

---

## Customer Terms

### Approved Clauses

#### Hybrid Storage Disclosure
> *"Your interaction data is temporarily stored on the Smart Companion (Model MC-110) for real-time functionality (max 24 hours). When your Link Device (Model LD-115) is within proximity (≤3 meters), data is encrypted and transferred to the secure primary datastore on the Link Device. Upon successful synchronization, data is automatically erased from the Smart Companion within 5 seconds."*

**✅ Compliance Check:**
- [x] Accurately reflects Hybrid Storage (products.md §Storage Architecture)
- [x] Specifies erasure timeline (≤5 seconds) (compliance.md §Automatic Data Erasure)
- [x] Warns of data loss risk if sync fails

#### Biometric Consent (GDPR/PDPO)
> *"You explicitly consent to the collection and processing of biometric data (facial recognition, optical position tracking via Model OS-2026) for: (1) authenticating your identity; (2) adjusting animation and tone based on your position and mood; (3) improving persona model accuracy. You may withdraw consent at any time via Settings > Privacy, which may limit Service functionality."*

**✅ Compliance Check:**
- [x] Explicit opt-in language (compliance.md §GDPR)
- [x] Specific purposes stated; withdrawal mechanism described
- [x] Complies with PDPO/GDPR biometric requirements

#### Liability Cap (Customer-Facing)
> *"To the maximum extent permitted by Hong Kong law, Company's total liability arising out of or related to these Terms or the Service shall not exceed USD $100 or the amount you paid for the Service in the twelve (12) months preceding the claim, whichever is greater. In no event shall Company be liable for indirect, incidental, special, consequential, or punitive damages."*

**✅ Compliance Check:**
- [x] Includes liability cap (compliance.md §Data Breach Liability)
- [x] Excludes consequential damages
- [x] Complies with Hong Kong law limitations

---

### Flagged Patterns

#### False Data Retention Claim
> *"All user data is stored permanently on the Smart Companion device for immediate access."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Automatic Data Erasure (products.md §Storage Architecture)
- **Risk:** Misleading disclosure; contradicts hybrid storage + erasure policy
- **Fix:** Use approved Hybrid Storage Disclosure clause

#### IP Ownership of User Data
> *"By using the Service, you grant Company exclusive ownership of all data generated during interactions, including memory cards and biometric inputs."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §User Data IP (Company does not claim IP over user data)
- **Risk:** GDPR/PDPO non-compliant; reputational damage
- **Fix:** Disclaim IP ownership; limit to limited license for service improvement

#### Uncapped Liability
> *"Company shall be liable for all damages arising from use of Service, including consequential and punitive damages."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Data Breach Liability (Liability Cap)
- **Risk:** Unlimited exposure for health data breaches
- **Fix:** Use approved Liability Cap clause

---

### Corrections (Captured from Sessions)

| Date | Original Clause | Issue | Corrected Language |
| :--- | :--- | :--- | :--- |
| Jan 28, 2026 | "Data retained on Companion for 12 months." | Conflicts with automatic erasure policy | Changed to "Data temporarily stored ≤24h; erased within 5s of sync confirmation" |
| Feb 1, 2026 | "Company owns all user-generated data." | Violates User Data IP rule | Changed to "User retains all rights; Company receives limited license for service improvement" |

---

## Compliance & Regulatory

### Approved Clauses

#### Breach Notification (DPA)
> *"Processor shall notify Controller without undue delay and in any event within twenty-four (24) hours of becoming aware of a Personal Data breach. Notification shall include: nature of the breach, categories and approximate number of Data Subjects affected, likely consequences, and measures taken or proposed to address the breach."*

**✅ Compliance Check:**
- [x] Timeline ≤24 hours (stricter than GDPR 72h) (compliance.md §Standing Flags)
- [x] Includes required content details
- [x] Complies with GDPR/PDPO

#### Data Erasure Certification
> *"Upon termination or Controller's request, Processor shall securely erase all Personal Data using cryptographic shredding (NIST 800-88 compliant) and provide written certification of destruction within 10 business days."*

**✅ Compliance Check:**
- [x] Specifies erasure method (cryptographic shredding)
- [x] Includes certification requirement (audit trail)
- [x] Aligns with compliance.md §Automatic Data Erasure

#### Cross-Border Transfer Safeguards
> *"Where Personal Data is transferred outside Hong Kong or the EEA, Processor shall ensure an appropriate transfer mechanism is in place (e.g., EU Standard Contractual Clauses, Binding Corporate Rules, or adequacy decisions) and provide Controller with copies upon request."*

**✅ Compliance Check:**
- [x] Complies with GDPR Chapter V and PDPO cross-border requirements
- [x] Requires documentation provision to Controller

---

### Flagged Patterns

#### Delayed Breach Notification
> *"Processor shall notify Controller of data breaches within 7 days of discovery."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §GDPR (72-hour notification requirement)
- **Risk:** Regulatory fines; non-compliant with internal 24h standard
- **Fix:** Change timeline to ≤24 hours (internal standard) or ≤72 hours (GDPR minimum)

#### Vague Erasure Method
> *"Processor shall delete Personal Data upon request."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Automatic Data Erasure (must specify method)
- **Risk:** Inadequate destruction; audit failure
- **Fix:** Specify "cryptographic shredding (NIST 800-88 compliant)" + certification

#### Missing Transfer Mechanism
> *"Processor may transfer Personal Data to subprocessors in any jurisdiction."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Other Obligations (PDPO/GDPR cross-border rules)
- **Risk:** Illegal data transfer; regulatory penalties
- **Fix:** Require appropriate transfer mechanism (SCCs, BCRs, adequacy)

---

### Corrections (Captured from Sessions)

| Date | Original Clause | Issue | Corrected Language |
| :--- | :--- | :--- | :--- |
| Jan 28, 2026 | "Breach notification within 7 days." | Too slow for GDPR/internal standard | Changed to "within 24 hours of becoming aware" |
| Feb 1, 2026 | "Data deleted upon request." | Vague; no method specified | Changed to "cryptographic shredding (NIST 800-88) + written certification" |

---

## Library Maintenance Notes

- **Last Full Review:** February 1, 2026 (Andrew Leung, Chief Legal Officer)
- **Next Scheduled Review:** May 1, 2026 (Quarterly)
- **Process for Adding New Clauses:**
  1. Draft clause aligned with compliance.md + products.md
  2. Legal review + compliance check against Standing Flags
  3. If approved, add to "Approved Clauses" with ✅ Compliance Check
  4. If flagged, add to "Flagged Patterns" with ⚠️ Flag Reason + Fix
  5. Capture corrections from negotiations in "Corrections" table
- **Agent Usage:** Always consult this library before generating new clause language. If a generated clause matches a "Flagged Pattern," auto-suggest the "Corrected Language" from the table.