# Legal Contracts Demo

Use this deployment as a context-first legal review surface.

## Start

```bash
cd /Users/andrew/backup/work/simply-connect-workspace/deployments/legal-contracts
sc --role reviewer
```

## Good prompts

```text
Review Contract-PDF-Samples/contract1_hardware_supplier_agreement.md for high-risk clauses.
Review Contract-PDF-Samples/contract2_ip_licensing_agreement.md for IP ownership and field-of-use risks.
Check Contract-PDF-Samples/contract5_data_processing_agreement.md against GDPR and HIPAA obligations.
Explain the top issues in Contract-PDF-Samples/contract8_apac_distribution_agreement.md for a non-lawyer.
```

## Demo point

- `sc-admin review` is framework approval only
- legal judgment stays in domain roles
- different roles express the same legal context through different lenses
