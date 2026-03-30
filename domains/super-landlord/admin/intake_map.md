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

### Typical workflow

```bash
# 1. Ingest utility bills into staging
sc ingest water-bill-march.pdf            # → staging (utilities)
sc ingest electricity-bill-q1.jpg         # → staging (utilities)
sc ingest maintenance-invoice.txt         # → staging (debit_notes)

# 2. Framework review and approve
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
