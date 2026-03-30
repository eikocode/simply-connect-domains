# simply-connect-domains

Domain library for [simply-connect](https://github.com/your-org/simply-connect).

Each domain is a self-contained deployment template: profile, context schema, role definitions, and extension (API integration).

## Domains

| Domain | Description | Extension |
|---|---|---|
| `decision-pack` | Multi-role underwriting workflow around one canonical Decision Pack | — |
| `minpaku` | Short-term rental management with live booking data | Minpaku API |
| `super-landlord` | Property management, utility bills, debit notes | — |

## Usage

Point `sc-admin init` at this library:

```bash
# Set once in your .env or shell profile
export SC_DOMAINS_DIR=/path/to/simply-connect-domains/domains

# Initialise a deployment
sc-admin init minpaku
sc-admin init super-landlord
```

Or clone this repo next to your `simply-connect` installation — it will be found automatically:

```
your-workspace/
  simply-connect/           # engine
  simply-connect-domains/   # this repo
```

## Domain structure

```
domains/
  {name}/
    profile.json      # context schema, extensions, roles
    AGENT.md          # agent instructions
    context/          # skeleton context files
    roles/            # per-role AGENT.md files (if multi-role)
    admin/            # intake_map.md
    extension/        # tools.py + client.py (if API integration)
```
