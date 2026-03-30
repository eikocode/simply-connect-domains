# HARDWARE SUPPLIER AGREEMENT

**Effective Date:** January 14, 2026  
**Agreement No.:** HSA-2026-001-HK  
**Parties:**  
- **Buyer:** Memora Technologies Limited, a company incorporated in Hong Kong with its principal place of business at 18/F, Tower One, Lippo Centre, 89 Queensway, Admiralty, Hong Kong ("Buyer")  
- **Supplier:** Precision Components Ltd., a company incorporated in Singapore with its principal place of business at 10 Science Park Road, #02-01 The Alpha, Singapore 117684 ("Supplier")  

**Governing Law:** Hong Kong Special Administrative Region  

---

## 1. SCOPE OF SUPPLY

1.1 Supplier shall provide the following components per Exhibit A:
- **Optical Sensor Module (Model OS-2026):** OmniVision OV9282 global shutter CMOS for user position tracking (±2cm accuracy) and facial expression analysis.
- **Link Device Enclosure (Model LD-115):** Housing for primary datastore, designed **without input/output elements** (no screen, buttons, ports, or speakers).

1.2 All components shall conform to the technical specifications in Exhibit A and Buyer's quality standards.

## 2. PRICING AND PAYMENT

2.1 Prices are fixed in **United States Dollars (USD)** as specified in Exhibit B.
- Optical Sensor Module: USD $45.00 per unit.
- Link Device Enclosure: USD $22.50 per unit.

2.2 Payment terms: Net 30 days from date of invoice. Late payments incur interest at 1.5% per month.

2.3 All prices are exclusive of Hong Kong taxes, duties, or import fees, which shall be borne by Buyer unless otherwise agreed.

## 3. INTELLECTUAL PROPERTY OWNERSHIP

3.1 **Work Product.** All inventions, designs, improvements, or works of authorship created by Supplier in connection with this Agreement—including modifications to the **secure link device architecture** or **proximity-triggered data synchronization logic**—shall be solely owned by Buyer.

3.2 **Supplier Background IP.** Supplier retains ownership of pre-existing intellectual property. Supplier grants Buyer a perpetual, irrevocable, royalty-free, worldwide license to use Supplier Background IP as embedded in the supplied components.

3.3 **IP Assignment.** Supplier hereby assigns to Buyer all right, title, and interest in any derivative works, improvements, or adaptations of the link device architecture, including designs that eliminate user-accessible I/O elements for security purposes.

## 4. CONFIDENTIALITY

4.1 Supplier shall not disclose Buyer's proprietary information, including:
- Hybrid storage architecture (local temporary storage → secure primary storage → automatic erasure).
- Algorithm integration with persona models and multimodal interaction.
- Technical specifications for optical sensors and link devices.

4.2 Confidentiality obligations survive termination of this Agreement for five (5) years.

## 5. INDEMNIFICATION AND LIABILITY

5.1 **Supplier Indemnity.** Supplier shall indemnify, defend, and hold harmless Buyer from third-party claims alleging that supplied components infringe intellectual property rights.

5.2 **Liability Cap.** Except for breaches of confidentiality, IP infringement, or gross negligence, Supplier's total liability under this Agreement shall not exceed **USD $500,000** or twelve (12) months of fees paid under this Agreement, whichever is less.

5.3 **Exclusion of Consequential Damages.** Neither party shall be liable for indirect, incidental, special, or consequential damages, including loss of profits or data.

## 6. DATA SECURITY

6.1 Supplier shall implement industry-standard encryption for all data transmitted during component testing.

6.2 Supplier shall not retain any user data from testing activities and shall certify destruction upon completion.

## 7. TERM AND TERMINATION

7.1 Initial term: Three (3) years from Effective Date, automatically renewable for one (1) year periods unless either party provides ninety (90) days' written notice of non-renewal.

7.2 Either party may terminate for material breach with thirty (30) days' written notice and opportunity to cure.

## 8. GOVERNING LAW AND DISPUTE RESOLUTION

8.1 This Agreement shall be governed by and construed in accordance with the laws of the **Hong Kong Special Administrative Region**.

8.2 Any dispute arising out of or in connection with this Agreement shall be submitted to the exclusive jurisdiction of the courts of Hong Kong.

---

**IN WITNESS WHEREOF**, the parties have executed this Agreement as of the Effective Date.

**BUYER:**  
Memora Technologies Limited  
By: _/s/ Elena Rossi_  
Name: Elena Rossi  
Title: Chief Technology Officer  
Date: January 14, 2026  

**SUPPLIER:**  
Precision Components Ltd.  
By: _/s/ David Tan_  
Name: David Tan  
Title: Director of Sales  
Date: January 14, 2026  

---

## Exhibit A: Component Specifications

**1. Optical Sensor Module (Model OS-2026)**
- **Sensor Type:** Global Shutter CMOS (OmniVision OV9282 equivalent).
- **Resolution:** 1280 x 800 pixels.
- **Frame Rate:** 60 fps minimum.
- **Latency:** ≤50ms end-to-end processing for position tracking.
- **Accuracy:** User position tracking ±2cm; Facial expression analysis confidence ≥95%.
- **Interface:** MIPI CSI-2.
- **Power:** ≤500mW average.
- **Operating Temp:** 0°C to 45°C.

**2. Link Device Enclosure (Model LD-115)**
- **Dimensions:** 100mm x 100mm x 30mm.
- **Material:** Aluminum alloy (IP54 rated).
- **I/O Constraints:** **ZERO** external ports, buttons, screens, speakers, or microphones.
- **Access:** Internal NVMe slot accessible only via proprietary tool (Supplier provided).
- **Tamper Evidence:** Seals must show visible damage if opened.
- **PAN Antenna:** Integrated Nordic nRF52840 compatible antenna (2.4GHz).
- **Security:** Tamper-evident seals required on all enclosure seams.

## Exhibit B: Pricing Schedule (USD)

| Item | Model No. | Unit Price (USD) | MOQ | Lead Time |
| :--- | :--- | :--- | :--- | :--- |
| Optical Sensor Module | OS-2026 | $45.00 | 1,000 units | 8 weeks |
| Link Device Enclosure | LD-115 | $22.50 | 5,000 units | 6 weeks |
| Custom Firmware License | FW-SEC-01 | $10,000 (One-time) | N/A | 4 weeks |
| **Total Initial Order** | **Mixed** | **$250,000 (Est.)** | **See Above** | **8 weeks** |

## Exhibit C: IP Assignment Form

**ASSIGNMENT OF INTELLECTUAL PROPERTY RIGHTS**

**Assignor:** Precision Components Ltd.  
**Assignee:** Memora Technologies Limited  
**Date:** January 14, 2026  

For good and valuable consideration, the receipt and sufficiency of which are acknowledged, Assignor hereby assigns to Assignee all right, title, and interest in and to any inventions, designs, improvements, or works of authorship created by Assignor in connection with Hardware Supplier Agreement No. HSA-2026-001-HK, specifically including:
1.  Modifications to the Link Device Enclosure (Model LD-115) that eliminate user-accessible I/O elements.
2.  Firmware improvements related to PAN-triggered data synchronization logic.
3.  Any manufacturing processes developed specifically for Buyer's secure storage architecture.

**Signed:**  
_/s/ David Tan_  
David Tan, Director of Sales  
Precision Components Ltd.

## Exhibit D: Quality Assurance Standards

- **Defect Rate:** ≤500 PPM (Parts Per Million).
- **Testing:** 100% functional testing on Optical Sensors; 10% random sampling on Enclosures.
- **Certification:** ISO 9001:2015 certified manufacturing facility required.
- **Inspection:** Buyer reserves the right to conduct quarterly audits at Supplier's facility with 14 days' notice.
- **Returns:** Defective units must be replaced within 10 business days at Supplier's expense.