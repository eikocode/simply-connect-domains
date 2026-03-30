# AIOS → Super-Landlord Intake Map

Reference document for `sc-admin intake` with the super-landlord profile.

---

## Mapping

| AIOS File | AIOS Section | → Context File | Category |
|---|---|---|---|
| `context/business-info.md` | Organization Overview | `context/properties.md` | properties |
| `context/personal-info.md` | Role / function | `context/tenants.md` | tenants |
| `context/current-data.md` | Key metrics | `context/utilities.md` | utilities |

---

## Primary Intake Path: Document Ingestion

For this profile, the primary intake path is **document ingestion**, not AIOS transfer.

Recommended parser for local bill ingestion:

```bash
cd /Users/andrew/backup/work/simply-connect-workspace/simply-connect
source .venv/bin/activate
pip install -e '.[local-ingest]'
export SC_DOCUMENT_PARSER=docling
```

This avoids the need for `ANTHROPIC_API_KEY` when ingesting JPG/PNG/PDF utility bills locally.

### Typical workflow

```bash
# 1. Ingest utility bills
sc-admin ingest water-bill-march.pdf       # → staging (utilities)
sc-admin ingest electricity-bill-q1.jpg   # → staging (utilities)
sc-admin ingest maintenance-invoice.txt   # → staging (debit_notes)

# 2. Review and approve
sc-admin review                           # → commit to context/

# 3. Generate debit notes
sc                                        # operator session
# "generate debit note for Unit 2A for March water charges"
```

### What gets extracted from bills

| Document type | Extracted fields |
|---|---|
| Utility bill | Provider, account number, service period, total amount, due date, service address |
| Invoice | Supplier, invoice number, date, line items, total, due date |
| Lease agreement | Tenant name, unit, lease term, rent amount, utility responsibilities |
