# belacca.com platform workspace

Single-checkout workspace for the public multi-project platform behind
[`belacca.com`](https://belacca.com).

This repository is an **orchestrator only**. Application and deployment history
remain in their own repositories:

| Directory | Repository | Responsibility |
|---|---|---|
| `cloudnativepong/` | [`macel94/cloudnativepong`](https://github.com/macel94/cloudnativepong) | Pong application, images, app manifests |
| `francesco-belacca-site/` | [`macel94/francesco-belacca-site`](https://github.com/macel94/francesco-belacca-site) | Personal site, image, site manifests |
| `belacca-gitops/` | [`macel94/belacca-gitops`](https://github.com/macel94/belacca-gitops) | Flux root, cluster infrastructure, host routing |

The submodules are pinned to known commits. The parent repository does not
flatten or duplicate their files, so each project can still be reviewed, built,
and deployed independently.

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

The site's [`status.html`](francesco-belacca-site/status.html) and
[`status.json`](francesco-belacca-site/status.json) are a separate sanitized
public contract. The checked-in status is deliberately `unknown` /
`not_configured`; an external publisher must provide reviewed evidence before
any status or uptime value is shown. No page response, build identifier, or
empty incident list is treated as uptime evidence.

## Hosting map

- `https://pong.belacca.com/` → Cloud Native Pong
- `https://francesco.belacca.com/` → Francesco's personal site
- `https://belacca.com/` → redirect to the personal site
- `https://www.belacca.com/` → redirect to the personal site
- `https://dashboard.belacca.com/` → authenticated Headlamp Kubernetes dashboard

DNS records are managed outside GitHub at Cloudflare. Add these A records when
setting up a new machine or domain:

```text
pong.belacca.com       A 169.58.97.73
francesco.belacca.com  A 169.58.97.73
dashboard.belacca.com  A 169.58.97.73
```

## Safety model

- Do not delete or recreate the `k3d-pong` cluster from this workspace.
- Do not delete `pong-api-data`, its PV, or `kube-system/traefik-acme`.
- Flux ownership and migration rules are documented in
  `belacca-gitops/MIGRATION.md`.
- The repeatable public-subdomain procedure is documented in
  `belacca-gitops/SUBDOMAIN-RUNBOOK.md`.
- Parent updates only pin child commits; deployment happens through each
  project's GitHub Actions workflow and Flux reconciliation.
