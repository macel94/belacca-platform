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
| `belacca-gitops/` | [`macel94/belacca-gitops`](https://github.com/macel94/belacca-gitops) | Flux root, cluster infrastructure, host routing |

The application and deployment repositories are normally pinned to known
commits as submodules. The status repository is maintained separately and is
also checked out here for local review; its first published commit must exist
before the parent can record a valid submodule pointer. The parent repository
does not flatten or duplicate child history, so each project can still be
reviewed, built, and deployed independently.

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
make evidence-test # run bounded evidence-tool tests
make evidence-bundle # explicitly collect local evidence (read-only)
make update       # fetch and fast-forward submodules to their configured main branches
make validate     # run application tests and render Kubernetes manifests
make site-test    # portfolio tests
make pong-test    # Go tests, race tests, and vet
make manifests    # render Pong, site, and platform Kustomizations
```

For the fast development model, read
[`docs/development-loop.md`](docs/development-loop.md). Local process mode is
the default inner loop; the public `k3d-pong` cluster is not a development
sandbox, and GitOps is reserved for reviewed production promotion.

`make update` changes the checked-out submodule commits and stages the parent
Gitlinks, but does not commit or push. Review the resulting parent diff before
publishing a new workspace pin.

The helper scripts never stage or commit files inside a child repository. A
working tree such as `cloudnativepong/ops/` is intentionally reported but left
untouched.

## Incident evidence and public status

[`scripts/incident-evidence.sh`](scripts/incident-evidence.sh) is an explicitly
invoked, bounded, read-only collector for selected kubectl/Flux/workspace status
inputs. It emits local JSON/Markdown with timestamps, source references,
redactions, hypotheses, confidence, and pending human-approval placeholders.
It never queries Secret contents, mutates the cluster, or approves an action.
See [`docs/incident-evidence.md`](docs/incident-evidence.md) for the AI boundary:
read-only, evidence-linked, human approval, and GitOps-only production changes.

The site's [`status.html`](francesco-belacca-site/status.html) consumes a separate sanitized status artifact generated hourly by [`macel94/belacca-status`](https://github.com/macel94/belacca-status) from a GitHub-hosted runner outside the single VM. Fresh observations are displayed; stale or malformed remote data falls back to unknown. No page response, build identifier, or empty incident list is treated as uptime evidence.

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

- Do not delete or recreate the `k3d-pong` cluster from this workspace.
- Do not delete `pong-api-data`, its PV, or `kube-system/traefik-acme`.
- Flux ownership and migration rules are documented in
  `belacca-gitops/MIGRATION.md`.
- The repeatable public-subdomain procedure is documented in
  `belacca-gitops/SUBDOMAIN-RUNBOOK.md`.
- Parent updates only pin child commits; deployment happens through each
  project's GitHub Actions workflow and Flux reconciliation.
