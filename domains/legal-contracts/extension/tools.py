"""
Legal-contracts extension — deterministic contract review and compliance tools.

This extension provides:
- Fast pattern-match handlers for contract review queries
- Deterministic staging entry review for contract risk analysis
- Compliance flag validation against clause_library.md patterns
"""

from __future__ import annotations

import re
from typing import Any


def _is_operator_role(role_name: str) -> bool:
    return role_name in {"operator", "admin"}


TOOLS = []


def _extract_severity_keywords(text: str) -> list[str]:
    keywords = []
    lowered = text.lower()
    if any(kw in lowered for kw in ["high risk", "critical", "severe", "unacceptable"]):
        keywords.append("high")
    if any(kw in lowered for kw in ["medium", "moderate", "concern"]):
        keywords.append("medium")
    if any(kw in lowered for kw in ["low", "minor", "best practice"]):
        keywords.append("low")
    return keywords


def _extract_risk_categories(text: str) -> list[str]:
    categories = []
    lowered = text.lower()
    if any(kw in lowered for kw in ["liability", "indemnif", "damages", "cap"]):
        categories.append("liability")
    if any(kw in lowered for kw in ["ip", "ownership", "patent", "invention"]):
        categories.append("ip")
    if any(kw in lowered for kw in ["data", "privacy", "breach", "gdpr", "hipaa"]):
        categories.append("data")
    if any(kw in lowered for kw in ["confidential", "nda", "secret"]):
        categories.append("confidentiality")
    if any(kw in lowered for kw in ["termination", "expiry", "renew"]):
        categories.append("termination")
    return categories


def _parse_clause_pattern(content: str) -> dict[str, Any] | None:
    patterns = [
        (r"uncapped\s+liability", "liability", "Uncapped Liability"),
        (r"(?:unlimited|unrestricted)\s+.*?liability", "liability", "Unrestricted Liability"),
        (r"(?:perpetual|unlimited)\s+term", "termination", "Perpetual Term"),
        (r"joint\s+ownership", "ip", "Joint Ownership"),
        (r"waive.*?(?:indemnif|liability)", "liability", "Liability Waiver"),
        (r"(?:12|twelve)\s*month.*?notice", "termination", "Long Notice Period"),
    ]
    for pattern, category, label in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return {"category": category, "label": label, "pattern": pattern}
    return None


def _load_clause_library(cm) -> dict[str, Any]:
    library = {"approved": {}, "flagged": {}}
    try:
        content = cm.load_committed().get("clause_library", "")
        if not content:
            return library
        
        sections = re.split(r"(?=^###\s+)", content, flags=re.MULTILINE)
        current_section = None
        for section in sections:
            if section.startswith("### Approved"):
                current_section = "approved"
            elif section.startswith("### Flagged"):
                current_section = "flagged"
            elif current_section:
                heading = re.search(r"^####\s+(.+)$", section, re.MULTILINE)
                if heading:
                    key = heading.group(1).strip()
                    library[current_section][key] = section
    except Exception:
        pass
    return library


def _check_clause_against_library(clause_text: str, library: dict[str, Any]) -> dict[str, Any] | None:
    for label, content in library.get("flagged", {}).items():
        if re.search(r"Flag Reason", content, re.IGNORECASE):
            flagged_pattern = re.search(r"Violates:\s*(.+?)(?:\n|$)", content)
            if flagged_pattern:
                return {
                    "status": "flagged",
                    "label": label,
                    "violation": flagged_pattern.group(1).strip(),
                }
    
    for label, content in library.get("approved", {}).items():
        if "Compliance Check" in content:
            return {
                "status": "approved",
                "label": label,
            }
    return None


def _parse_contract_reference(text: str) -> dict[str, str | None]:
    patterns = [
        r"(?:contract|agreement)\s+([A-Z]{2,}(?:-[0-9]+)+)",
        r"(?:HSA|IPL|DPA|NDA|MSA)-([0-9]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return {"type": "contract_id", "value": match.group(0)}
    
    if "hardware" in text.lower():
        return {"type": "contract_type", "value": "hardware supplier"}
    if "ip" in text.lower() or "license" in text.lower():
        return {"type": "contract_type", "value": "ip license"}
    if "data" in text.lower() or "dpa" in text.lower():
        return {"type": "contract_type", "value": "dpa"}
    if "nda" in text.lower():
        return {"type": "contract_type", "value": "nda"}
    if "distribution" in text.lower():
        return {"type": "contract_type", "value": "distribution"}
    return {}


def maybe_handle_message(message: str, cm, role_name: str = "operator") -> str | None:
    if not _is_operator_role(role_name):
        return None
    
    text = " ".join(message.strip().split())
    lowered = text.lower()
    
    if not text:
        return None
    
    if "risk" in lowered and ("flag" in lowered or "check" in lowered or "review" in lowered):
        contract_ref = _parse_contract_reference(text)
        clause_pattern = _parse_clause_pattern(text)
        
        if clause_pattern:
            library = _load_clause_library(cm)
            check_result = _check_clause_against_library(text, library)
            
            if check_result:
                if check_result["status"] == "flagged":
                    return (
                        f"⚠️ **Flagged Pattern Detected**\n\n"
                        f"- Category: `{check_result['label']}`\n"
                        f"- Violates: {check_result['violation']}\n"
                        f"\n"
                        f"**Recommendation:** Replace with approved clause language from the clause library.\n"
                        f"**Next:** Ask counsel to draft compliant replacement language."
                    )
                elif check_result["status"] == "approved":
                    return (
                        f"✅ **Approved Pattern Found**\n\n"
                        f"- Pattern: `{check_result['label']}`\n"
                        f"- Status: Matches approved clause language\n"
                        f"\n"
                        f"This pattern aligns with our compliance requirements."
                    )
        
        if contract_ref:
            return (
                f"Contract reference detected: `{contract_ref.get('value')}`\n\n"
                f"To perform a full risk review, use:\n"
                f"- `sc review` — review staged contract notes\n"
                f"- `counsel: review <contract>` — detailed clause analysis\n"
                f"- `reviewer: flag risks in <contract>` — severity-first findings"
            )
        
        return (
            "I can check staged contract notes for risk flags.\n\n"
            "Use `sc review` to check staging, or specify:\n"
            "- `reviewer: check <contract-id> for high-risk clauses`\n"
            "- `counsel: flag any compliance issues in staging`"
        )
    
    if any(phrase in lowered for phrase in ["show contracts", "list contracts", "active contracts"]):
        try:
            contracts = cm.load_committed().get("contracts", "")
            if contracts:
                active_section = re.search(r"##\s+Active Contracts.*?(?=---|$)", contracts, re.DOTALL | re.IGNORECASE)
                if active_section:
                    return (
                        f"## Active Contracts\n\n{active_section.group(0)}\n\n"
                        f"Full contract details in `contracts.md`. "
                        f"Use `counsel: show draft <contract>` for details."
                    )
        except Exception:
            pass
        return "No active contracts found in committed context."
    
    if "clause library" in lowered or "approved clauses" in lowered:
        library = _load_clause_library(cm)
        if library.get("approved"):
            lines = ["## Approved Clause Patterns", ""]
            for label in list(library["approved"].keys())[:5]:
                lines.append(f"- {label}")
            lines.extend(["", "Use these patterns for new contract language."])
            return "\n".join(lines)
        return "Clause library is empty. Check `clause_library.md` in context."
    
    return None


def review_staging_entry(cm, entry: dict) -> dict[str, Any] | None:
    content = entry.get("content", "")
    category = entry.get("category", "")
    
    if category not in {"contracts", "compliance", "clause_library"}:
        return None
    
    flagged_patterns = []
    approved_patterns = []
    
    clause_pattern = _parse_clause_pattern(content)
    if clause_pattern:
        library = _load_clause_library(cm)
        check_result = _check_clause_against_library(content, library)
        
        if check_result and check_result["status"] == "flagged":
            flagged_patterns.append(check_result["label"])
        elif check_result and check_result["status"] == "approved":
            approved_patterns.append(check_result["label"])
    
    gdpr_hipaa_violations = []
    if re.search(r"breach.*?(?:notify|report).*?(?:\d+|days|hours)", content, re.IGNORECASE):
        if not re.search(r"24.*hour|twenty.?four", content, re.IGNORECASE):
            gdpr_hipaa_violations.append("Breach notification timeline too long (>24h)")
    if re.search(r"(?:unlimited|uncapped).*?liability", content, re.IGNORECASE):
        gdpr_hipaa_violations.append("Unlimited liability exposure")
    
    if flagged_patterns or gdpr_hipaa_violations:
        return {
            "recommendation": "defer",
            "reason": f"Found {len(flagged_patterns)} flagged clause pattern(s) and {len(gdpr_hipaa_violations)} compliance concern(s).",
            "conflicts": flagged_patterns + gdpr_hipaa_violations,
            "suggested_category": "compliance",
            "confidence": 0.9,
        }
    
    if approved_patterns:
        return {
            "recommendation": "approve",
            "reason": "Staged content aligns with approved clause patterns.",
            "conflicts": [],
            "suggested_category": category,
            "confidence": 0.85,
        }
    
    return None


def on_staging_approved(cm, entry: dict) -> dict[str, Any] | None:
    content = entry.get("content", "")
    category = entry.get("category", "")
    
    if category == "contracts":
        contract_id_match = re.search(r"([A-Z]{2,}(?:-[0-9]+)+)", content)
        if contract_id_match:
            contract_id = contract_id_match.group(1)
            timestamp = entry.get("captured", "").split("T")[0]
            note = f"\n\n## {contract_id}\n- Status update captured: {timestamp}\n- Source: staging approval"
            cm.update_committed("contracts", note)
            return {"ok": True, "message": f"Contract {contract_id} status updated.", "contract_id": contract_id}
    
    if category == "clause_library":
        if "approved" in content.lower():
            section_match = re.search(r"^###\s+(.+)$", content, re.MULTILINE)
            if section_match:
                cm.update_committed("clause_library", content)
                return {"ok": True, "message": "Clause library updated."}
    
    return None