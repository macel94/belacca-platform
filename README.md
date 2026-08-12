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
make evidence-bundle # explicitly collect local evidence (read-only)
make update       # fetch and fast-forward submodules to their configured main branches
make validate     # run application tests and render Kubernetes manifests
make site-test    # portfolio tests
make pong-test    # Go tests, race tests, and vet
make manifests    # validate and render Pong/site plus native production Kustomizations
make manifests-native-edge # compatibility check for native production and edge renders
make manifests-historical  # explicitly render retired old-production manifests for audit
```

## Migration state

The migration is now cut over to native k3s:

- **native-production:** the three-server native k3s cluster owns public
  application traffic. Cloudflare DNS-only A records for all application
  hostnames contain `.73`, `.41`, and `.42`; `k3s-api.belacca.com` remains
  `.41` and `.42` only.
- Native Flux, Traefik, cert-manager, TLS, Pong, portfolio, GoatCounter,
  Dex, Headlamp, and Flux Web are healthy. Pong, GoatCounter, and Dex SQLite
  state was quiesced, integrity-checked, restored into Longhorn-backed RWO
  PVCs, and verified in native workloads.
- **retired-old-production:** the former `k3d-pong` Podman cluster and its
  auto-start unit were removed after the controlled handoff. Its local PVCs are
  not a rollback target; external backup provisioning remains an accepted
  follow-up risk.

The final operational state and accepted risks are tracked in the host-level migration plan and the GitOps ownership rules below.
The host-level companion plan is in
[`belacca-infrastructure/docs/MIGRATION-PLAN.md`](belacca-infrastructure/docs/MIGRATION-PLAN.md);
[`belacca-gitops/MIGRATION.md`](belacca-gitops/MIGRATION.md) documents
Kubernetes ownership and cutover rules.

Native production is the live production plane, **not a development sandbox**.
Do not use it for iterative source edits, temporary image patches, or
experiments. For the fast development model, read
[`docs/development-loop.md`](docs/development-loop.md). Use local process mode
or an explicitly disposable, isolated development environment until a separate
warm development plane exists. GitOps is reserved for reviewed promotion.

`make update` changes the checked-out submodule commits and stages the parent
Gitlinks, but does not commit or push. Review the resulting parent diff before
publishing a new workspace pin.

Dependabot is configured daily in every public repository for each supported
ecosystem present: Git submodules and GitHub Actions in this workspace,
GitHub Actions in GitOps and infrastructure, npm in status, npm/Docker in the
portfolio, and Go modules/npm/Docker/GitHub Actions in Pong. The infrastructure
repository has no package, Docker, or language-module manifest for Dependabot
to update; its pinned k3s installer version and Debian package set remain
explicit infrastructure inputs rather than Dependabot-supported ecosystems.

The helper scripts never stage or commit files inside a child repository. A
working tree such as `cloudnativepong/ops/` is intentionally reported but left
untouched.

## Incident lifecycle, evidence, and public status

[`docs/incident-lifecycle.md`](docs/incident-lifecycle.md) defines the concise
incident lifecycle: declare early, assign an Incident Commander (IC),
Operations Lead, Communications Lead, and Planning/Follow-up Lead, maintain a
UTC timeline with evidence source IDs/timestamps, hand off explicitly, recover,
and close against written criteria. It defines SEV-1 through SEV-4 and
objective postmortem triggers for user-facing critical failure, monitoring
failure, data integrity/security events, a missed approved recovery objective,
and repeat/noisy incidents. It also contains sanitized incident-state and
blameless postmortem templates.

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
The public objective is 99% availability over 30 days per service with no SLA;
the separate controlled-drill objective is P95 recovery under six minutes. The
controlled-drill evidence contract and fail-closed operator runbook are in
[`docs/controlled-drill-recovery.md`](docs/controlled-drill-recovery.md); its
validator never executes a drill or targets the live public endpoint. A short
disposable baseline or evidence snapshot cannot prove either objective.

The site's [`status.html`](francesco-belacca-site/status.html) consumes a separate sanitized status artifact generated hourly by [`macel94/belacca-status`](https://github.com/macel94/belacca-status) from a GitHub-hosted runner outside the native cluster. Fresh observations are displayed; stale or malformed remote data falls back to unknown. No page response, build identifier, or empty incident list is treated as uptime evidence.

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

- The former `k3d-pong` cluster is retired; do not recreate it from this
  workspace. Native k3s is production; do not use it as a development sandbox.
- Do not delete `pong-api-data`, its PV, or `kube-system/traefik-acme`.
- Flux ownership and migration rules are documented in
  `belacca-gitops/MIGRATION.md`.
- The repeatable public-subdomain procedure is documented in
  `belacca-gitops/SUBDOMAIN-RUNBOOK.md`.
- Parent updates only pin child commits; deployment happens through each
  project's GitHub Actions workflow and Flux reconciliation.
