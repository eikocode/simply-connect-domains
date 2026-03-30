# Flagged Clause Library (Test Cases)
**Status:** ⚠️ Requires Legal Review  
**Last Updated:** January 14, 2026  
**Usage:** These clauses violate `compliance.md` Standing Flags. Agent should flag these for revision.

---

## 1. Uncapped Liability (Supplier Agreement)
> *"Supplier shall be liable for all damages arising from use of components, including consequential, indirect, and punitive damages. There is no limit on Supplier's total liability under this Agreement."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Data Breach Liability (Liability Cap).
- **Risk:** Unlimited exposure for health data breaches.
- **Fix:** Add cap (e.g., USD $500,000) and exclude consequential damages.

---

## 2. Conflicting Data Retention (Customer Terms)
> *"Smart Companion shall retain all user interaction data, memory cards, and learning states for 12 months for service improvement purposes, regardless of synchronization status."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Automatic Data Erasure (products.md §Storage Architecture).
- **Risk:** Contradicts automatic erasure policy (≤24h local retention); increases privacy risk.
- **Fix:** Align with erasure policy (erase within 5s of sync).

---

## 3. IP Ownership of User Data (Customer Terms)
> *"By using the Service, User grants Company exclusive ownership of all data generated during interactions, including memory cards, facial data, and conversation history. Company may license this data to third parties."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §User Data IP.
- **Risk:** Violates privacy policy; GDPR/PDPO non-compliant; reputational damage.
- **Fix:** Disclaim IP ownership; limit to limited license for service improvement.

---

## 4. Unrestricted Sublicensing (NDA)
> *"Receiving Party may share Confidential Information with its affiliates, contractors, and subprocessors without prior written consent from Disclosing Party."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Standing Flags (Sublicensing Rights).
- **Risk:** Core architecture leakage (Hybrid Storage, No I/O design).
- **Fix:** Require prior written consent for any third-party disclosure.

---

## 5. Non-Compliant Breach Notification (DPA)
> *"Processor shall notify Controller of data breaches within 7 days of discovery."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §GDPR (72-hour notification requirement).
- **Risk:** Regulatory fines (GDPR requires ≤72 hours).
- **Fix:** Change timeline to ≤24 hours (internal standard) or ≤72 hours (GDPR minimum).

---

## 6. Medical Claims (Customer Terms)
> *"This device diagnoses, treats, and cures cognitive decline, Alzheimer's disease, and memory loss. Users should rely on this device instead of professional medical advice."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Other Obligations (FDA/Non-Medical Positioning).
- **Risk:** FDA enforcement action; product classified as medical device requiring 510(k).
- **Fix:** Add medical disclaimer; position as "Wellness/Companion" only.

---

## 7. Joint IP Ownership (License Agreement)
> *"Any improvements or derivatives of the Licensed Algorithm created by Licensee shall be jointly owned by Licensor and Licensee."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §IP Ownership Rule (All IP owned by Company).
- **Risk:** Clouds ownership of core integration patents (DSR + Animation + Storage).
- **Fix:** Assign all improvements solely to Licensee (Memora).

---

## 8. Restrictive Field of Use (License Agreement)
> *"License is limited to educational applications. Use in healthcare, elderly care, or companion robotics requires separate written consent."*

**⚠️ Flag Reason:**
- **Violates:** compliance.md §Patent Strategy (Product Positioning).
- **Risk:** Blocks core business model (Elderly Companion).
- **Fix:** Expand Field of Use to include "Elderly Care" and "Companion Robotics".