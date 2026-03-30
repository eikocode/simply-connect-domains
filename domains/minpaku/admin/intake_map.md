# AIOS → Minpaku Intake Map

Reference document for `sc-admin intake` with the minpaku profile.

---

## Mapping

| AIOS File | AIOS Section | → Context File | Category |
|---|---|---|---|
| `context/business-info.md` | Organization Overview | `context/properties.md` | properties |
| `context/personal-info.md` | Role / function | `context/operations.md` | operations |
| `context/current-data.md` | Key metrics | `context/pricing.md` | pricing |

---

## Notes

- Live booking and property data is fetched via Minpaku API tools — no ingestion needed for that.
- Use `sc-admin ingest` for static documents: house rules PDFs, pricing sheets, contact lists.
- Committed context supplements the API — it holds configuration the API doesn't expose (house rules, SOPs, local contacts).
