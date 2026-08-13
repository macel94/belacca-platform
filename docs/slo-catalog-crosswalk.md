# SLO catalog crosswalk

The canonical service catalog remains
[`belacca-gitops/catalog/services.json`](https://github.com/macel94/belacca-gitops/blob/main/catalog/services.json).
This parent document records how the initial policy is represented there and
prevents the policy from being mistaken for a second host inventory.

The checked-out catalog is validated by
`belacca-gitops/scripts/validate-catalog.py`. It currently records, for
portfolio, Pong, analytics, and the protected dashboard service:

- owner (`platform`), public hosts, tier, dependencies, dashboard access, and
  runbook;
- proposed 99%/30d SLO status and the user journey indicator;
- the external hourly `belacca-status/slo.json` measurement source for the
  public services, with complete 720-slot evidence required before reporting;
  and
- the live native-production implementation path under
  `clusters/belacca-production/`.

The policy contract in [`slo-policy.json`](slo-policy.json) is the authoritative
cross-repository decision contract for the explicit numerator, denominator,
good/bad/unknown classification, 7.2-slot budget, review cadence, non-SLA
wording, and conditional operator-surface activation. When the child catalog is
next changed, its entries must remain consistent with that contract:

| Catalog service | Policy entry | Live implementation path | Evidence source |
|---|---|---|---|
| `portfolio` | `portfolio` | `clusters/belacca-production/native-applications.yaml` from `francesco-belacca-site/deploy` | `belacca-status:slo.json` |
| `pong` | `pong` | `clusters/belacca-production/native-applications.yaml`, live path `cloudnativepong/k8s/overlays/native-staging` | `belacca-status:slo.json` plus `cloudnativepong/scripts/synthetic-check.mjs` |
| `analytics` | `analytics` | `clusters/belacca-production/analytics` | `belacca-status:slo.json` |
| `dashboard` / protected operator surfaces | `operator-surfaces` | `clusters/belacca-production/headlamp`, `flux-web`, `dex`, and platform routing | **none until authenticated probe exists** |

The public SLOs remain proposed/not reportable in the checked-in evidence because
the current history does not contain a complete 720-slot window. The operator
surface entry remains `not_configured`; no credentials are present in the
public artifact or this parent repository. Do not mark either state live from a
render, a status-page response, or a single observation.

## Required catalog update on future service changes

1. Update the canonical GitOps catalog and `docs/SITES.md` together.
2. Keep owner, measurement source, review cadence, runbook, non-SLA wording,
   and native implementation path aligned with `slo-policy.json`.
3. Run the GitOps catalog/observability validators and this parent policy
   validator.
4. Record the evidence window, source references, limitations, and human review
   before changing `proposed`, `not_configured`, or `measured` status.

This crosswalk is intentionally documentation-only: it does not duplicate the
canonical host inventory or claim that a child-repository catalog change has
been deployed.
