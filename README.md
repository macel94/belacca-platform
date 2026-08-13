# belacca.com platform workspace

Single-checkout workspace for the public multi-project platform behind
[`belacca.com`](https://belacca.com).

This repository is an **orchestrator only**. Application and deployment history
remain in their own repositories:

| Directory | Repository | Responsibility |
|---|---|---|
| `cloudnativepong/` | [`macel94/cloudnativepong`](https://github.com/macel94/cloudnativepong) | Pong application, images, app manifests |
| `francesco-belacca-site/` | [`macel94/francesco-belacca-site`](https://github.com/macel94/francesco-belacca-site) | Personal site, image, site manifests |
| `belacca-status/` | [`macel94/belacca-status`](https://github.com/macel94/belacca-status) | Hourly external observations and sanitized status history |
| `belacca-gitops/` | [`macel94/belacca-gitops`](https://github.com/macel94/belacca-gitops) | Flux root, Kubernetes resources, host routing |
| `belacca-infrastructure/` | [`macel94/belacca-infrastructure`](https://github.com/macel94/belacca-infrastructure) | Host preparation, firewall posture, native k3s, storage prerequisites |

The application and platform repositories are pinned to known commits as
submodules. The status repository is maintained separately and is also checked
out here for local review; its first published commit must exist before the
parent can record a valid submodule pointer. The parent repository does not
flatten or duplicate child history, so each project can still be reviewed,
built, and deployed independently.

The native host foundation is included here through
`belacca-infrastructure/`, which owns host preparation, firewall posture,
native k3s configuration, and storage prerequisites. Kubernetes resources and
Flux ownership remain in `belacca-gitops/`.

## Clone everything

```bash
git clone --recurse-submodules https://github.com/macel94/belacca-platform.git
cd belacca-platform
make status
```

For an existing clone:

```bash
make init
```

## Useful commands

```bash
make status       # show parent and submodule branches/commits
make evidence-test # run bounded evidence-tool and contract tests
make drill-test   # run controlled-drill contract tests
make drill-validate RECORD=path/to/record.json # validate sanitized drill evidence (read-only)
make policy-test   # validate the internal SLO/error-budget policy and tests
make evidence-bundle # explicitly collect local evidence (read-only)
make update       # fetch and fast-forward submodules to their configured main branches
make validate     # run application tests and render Kubernetes manifests
make site-test    # portfolio tests
make pong-test    # Go tests, race tests, and vet
make manifests    # validate and render Pong/site plus native production Kustomizations
make manifests-native-edge # compatibility check for native production and edge renders
```

## Native production state

Native production is the only maintained platform plane: the three-server native
k3s cluster owns public application traffic, native Flux owns reconciliation,
and Longhorn-backed single-writer state is protected by the native runbooks.
Cloudflare DNS-only records for application hosts contain `.73`, `.41`, and
`.42`; `k3s-api.belacca.com` uses `.41` and `.42`.

Native production is not a development sandbox. Use local process mode or an
explicitly disposable isolated environment for development and experiments.
All production changes are reviewed GitOps changes through the native
`belacca-production` tree.

## Incident lifecycle, evidence, and public status

[`docs/incident-lifecycle.md`](docs/incident-lifecycle.md) defines the concise
incident lifecycle: declare early, assign an Incident Commander (IC),
Operations Lead, Communications Lead, and Planning/Follow-up Lead, maintain a
UTC timeline with evidence source IDs/timestamps, hand off explicitly, recover,
and close against written criteria. The local-only
[`scripts/incident-record.sh`](scripts/incident-record.sh) starts and validates
canonical JSON/Markdown records, attaches source IDs/timestamps without raw
output, and enforces the IC single-writer and GitOps-only change boundary. The
lifecycle defines SEV-1 through SEV-4 and objective postmortem triggers for
user-facing critical failure, monitoring failure, data integrity/security
events, a missed approved recovery objective, and repeat/noisy incidents. It
also contains sanitized incident-state and blameless postmortem templates,
review/closure criteria, and the completed fail-closed game-day postmortem at
[`docs/postmortems/2026-08-10-native-failure-game-day.md`](docs/postmortems/2026-08-10-native-failure-game-day.md).

[`scripts/incident-evidence.sh`](scripts/incident-evidence.sh) is an explicitly
invoked, bounded, read-only collector for selected kubectl/Flux/workspace status
inputs. It emits local JSON/Markdown with timestamps, source references,
redactions, hypotheses, confidence, and pending human-approval placeholders.
It never queries Secret contents, mutates the cluster, declares an incident, or
approves an action. Evidence is not proof of health: every claim must retain
its source ID, timestamp, status, and limitations. Templates and evidence must
not contain secrets, tokens, player data, or unredacted private telemetry.

There is no automatic approval or mutation capability in this documentation
or collector: only a human can interpret evidence, declare/close an incident,
approve an action, or communicate externally. Production changes—including emergency
rollback or traffic changes—remain reviewed, human-approved, tested where
possible, and GitOps-only through the appropriate repository and Flux path.
The internal SLO and error-budget decision policy is
[`docs/slo-error-budget-policy.md`](docs/slo-error-budget-policy.md), with the
machine-readable contract in [`docs/slo-policy.json`](docs/slo-policy.json) and
the target/live-capability checklist in
[`docs/slo-review-checklist.md`](docs/slo-review-checklist.md). The public
objective is 99% availability over 30 days per service with no SLA; the
separate controlled-drill objective is P95 recovery under six minutes. The
controlled-drill evidence contract and fail-closed operator runbook are in
[`docs/controlled-drill-recovery.md`](docs/controlled-drill-recovery.md); its
validator never executes a drill or targets the live public endpoint. A short
disposable baseline or evidence snapshot cannot prove either objective. The
policy distinguishes public status, durable SLO evidence, and paging. In-cluster
Alertmanager now routes Flux and Prometheus signals to Telegram; protected
operator surfaces still await an authenticated measurement path. Follow-up work is tracked as one GitHub issue per action using
[`docs/follow-up-issues.md`](docs/follow-up-issues.md).

The site's [`status.html`](francesco-belacca-site/status.html) consumes a separate sanitized status artifact generated hourly by [`macel94/belacca-status`](https://github.com/macel94/belacca-status) from a GitHub-hosted runner outside the native cluster. Fresh observations are displayed; stale or malformed remote data falls back to unknown with an “awaiting fresh evidence” explanation. Reported uptime is calculated from good and bad critical observations and includes its observation count; no page response, build identifier, or empty incident list is treated as uptime evidence.

## Supported platform sites

The canonical inventory of public applications, redirect aliases, operator
surfaces, DNS records, canonicalization rules, and monitoring coverage is
[`belacca-gitops/docs/SITES.md`](belacca-gitops/docs/SITES.md). Do not maintain
another host inventory in this workspace; update that document and the GitOps
routing/catalog together when a supported site changes.

In brief, `francesco.belacca.com` is the canonical personal site,
`pong.belacca.com` is Cloud Native Pong, and `stats.belacca.com` is the
analytics collector/dashboard. `belacca.com`, `www.belacca.com`, and
`www.francesco.belacca.com` permanently redirect to the canonical personal
site. `dashboard.belacca.com`, `flux.belacca.com`, and `dex.belacca.com` are
protected operator surfaces or aliases, not public applications.

## Safety model

- Native k3s is production; do not use it as a development sandbox.
- Do not delete `pong-api-data`, its PV, or `kube-system/traefik-acme`.
- Flux ownership and migration rules are documented in
  `belacca-gitops/MIGRATION.md`.
- The repeatable public-subdomain procedure is documented in
  `belacca-gitops/SUBDOMAIN-RUNBOOK.md`.
- Parent updates only pin child commits; deployment happens through each
  project's GitHub Actions workflow and Flux reconciliation.
