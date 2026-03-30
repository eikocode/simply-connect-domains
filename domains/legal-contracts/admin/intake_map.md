# Intake Map — legal-contracts

Maps AIOS context files to domain context files. Run `sc-admin intake` to import.

| AIOS Source | → Domain File | What Gets Imported |
|---|---|---|
| `business-info.md` | `products.md` | Product portfolio, hardware specs, software architecture, company overview |
| `personal-info.md` | `compliance.md` | User's role, regulatory obligations they manage, jurisdictions covered |
| `strategy.md` | `compliance.md` | Patent strategy, IP protection priorities, current legal focus areas |
| `current-data.md` | `contracts.md` | Active contracts, pipeline deals, pending negotiations |

## Notes

- `clause_library.md` and `counterparties.md` are not populated from AIOS intake — they are built up over time through agent sessions and document ingestion (`sc-admin ingest`).
- After intake, review `compliance.md` and `products.md` carefully — these are the most critical files for agent accuracy. Fill in all `[placeholder]` sections before beginning contract work.
- Ingest existing contracts and clause templates with `sc-admin ingest <file>` to seed `contracts.md` and `clause_library.md`.
