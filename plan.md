# Belacca native k3s migration — status and execution plan

**Status date:** 2026-08-09
**Document state:** migration complete; this plan now records post-cutover
operational hardening and evidence work.
**Scope:** migrate the former single-host `k3d-pong` platform on `.73` to a
three-server native k3s HA cluster without deleting or casually recreating
workloads, PVCs, or the production edge.

## Executive status

The native platform is now public production. The three-server native k3s
cluster, embedded etcd, Flux, SOPS/age, Longhorn, cert-manager, native Traefik,
TLS, routed Pong/portfolio, Dex, Headlamp, Flux Web, and analytics are healthy
and serve public traffic through DNS-only Cloudflare A records on `.41` and
`.42`. The former `k3d-pong` Podman cluster and auto-start unit on `.73` were removed
after a controlled state handoff.

Pong, GoatCounter, and Dex writers were quiesced. Their SQLite files were
copied, integrity-checked, restored into native Longhorn-backed RWO PVCs, and
verified by native startup and functional checks. Native Pong WebSocket journeys
pass on both edges; analytics collector paths and OIDC discovery/redirects pass.

The Cloudflare two-A arrangement is direct DNS round-robin, not health-aware
failover. External backups, authenticated browser completion, and a one-node
failure drill remain accepted operational follow-ups rather than blockers to
this operator-approved cutover.

Overall state: **native production cutover complete; hardening and retirement
follow-up remains.**

## This continuation’s completed work

- Began the approved cutover with Flux suspension, controlled writer
  quiescence, SQLite handoff, native Longhorn restore, and native workload
  verification.
- Published Cloudflare DNS-only A records for all application hostnames and
  `k3s-api.belacca.com` with `.41` and `.42` only; the former `.73` public
  records were removed. This is direct DNS round-robin, not health-aware
  failover.
- Published Pong native WebSocket origin correction `cloudnativepong@f46ceb8`.

- Audited the native edge, API endpoint, ACME design, documentation, and stale
  file candidates in parallel using tmux sessions with `openai/gpt-5.6-luna`.
- Confirmed that the old `belacca-gitops/clusters/vmi3474918` tree, protected
  ACME/PVC manifests, k3d systemd rollback service, infrastructure safeguards,
  CI/restore contracts, and encrypted key state must remain until cutover.
- Removed only the audited obsolete `cloudnativepong/clusters/vmi3474918/`
  child Flux tree and superseded historical `cloudnativepong/HANDOFF.md`.
- Removed the duplicate `cloudnativepong/k8s/all.yaml` after migrating CI and
  restore rehearsal to the explicit disposable `k8s/overlays/test/` overlay.
  Production remains `k8s/overlays/server/`; both overlays retain their own
  image/origin/PVC safety contracts.
- Updated infrastructure, GitOps, Pong, portfolio, parent-workspace, and native
  cluster documentation with the native-production/retired-old-production model.
- Hardened the native Traefik definition with explicit provider class filters,
  bounded CPU/memory, `minReadySeconds`, immutable image digest, and Flux root
  health checks for Longhorn and Traefik. The hardened edge was applied,
  validated, and published under Flux ownership.
- Added a native cert-manager `v1.21.1` controller/CRD-only boundary with
  immutable component image digests, bounded resources, retained CRDs, and a
  Flux health gate. No Cloudflare credential, DNS solver, Issuer, Certificate,
  route, or public DNS record is included.
- Added explicit Makefile rendering for both old-production and native GitOps
  roots so validation cannot silently check only one migration plane.

## What has been accomplished

### 1. Host onboarding and infrastructure baseline

- Audited all three Debian 13 VPSs. The two new servers are equivalent to the
  existing host at roughly 6 vCPUs, 11 GiB RAM, and 197 GiB disk.
- Created and published the private `macel94/belacca-infrastructure`
  repository with Ansible inventory, host preparation, k3s configuration,
  firewall policy, Longhorn prerequisites, and recovery documentation.
- Installed the dedicated automation SSH key on the new hosts and disabled
  password SSH on `.41` and `.42`. Key-based access is verified.
- Intentionally left the existing `.73` hostname and k3d-compatible firewall
  unchanged. Its SSH hardening remains a deliberate cutover task rather than
  an accidental production mutation.
- Prepared all hosts with required kernel modules, Kubernetes sysctls,
  inotify limits, iSCSI, NFS, cryptsetup, and Longhorn prerequisites.
- Restricted firewall rules are active on `.41` and `.42`; `.73` remains on its
  existing edge-compatible policy.

### 2. Native three-server HA k3s cluster

- Installed pinned native k3s `v1.35.5+k3s1` on all three hosts.
- Configured all three as control-plane/embedded-etcd servers:
  - `belacca-k3s-01` — `169.58.97.73`
  - `belacca-k3s-02` — `169.58.143.41`
  - `belacca-k3s-03` — `169.58.143.42`
- Disabled built-in k3s Traefik and ServiceLB so native ingress could be
  staged beside the existing k3d edge.
- Resolved the `.73` native-server join failure caused by host inotify
  exhaustion by increasing the host limits.
- Verified all three native nodes are `Ready`, the API `/readyz` endpoint is
  healthy, embedded etcd is operating, and metrics-server is healthy.
- Created DNS-only `k3s-api.belacca.com` A records for all three node IPs.
  Public DNS-over-HTTPS and the local resolver now return all three records;
  the k3s certificate contains the DNS name and all node IP SANs.
- The working operator kubeconfig still points directly to `.41` at
  `/root/.kube/belacca-native`. The DNS endpoint has been separately tested
  successfully, but a provider load balancer/floating-IP endpoint has not yet
  been selected.

### 3. Flux and encrypted secrets

- Bootstrapped Flux `v2.9.3` into the native `belacca-production` path.
- Native Flux source and root Kustomization are `Ready=True` at revision
  `c083165`. Native edge, cert-manager, TLS, routing, Pong, portfolio, Dex,
  Headlamp, Flux Web, and analytics Kustomizations are Flux-owned and Ready.
  Pong is at `f46ceb8`, and portfolio is at deployment revision `15808ea`.
  Public application DNS and `k3s-api.belacca.com` now resolve only to `.41`
  and `.42`; all native routes are tested directly and through pinned edges.
- Removed old-production OAuth, Cloudflare, analytics-admin, and proxy Secret
  manifests from native Git. Native Git contains only reviewed encrypted
  interfaces under `secrets/`; the out-of-band `flux-system/sops-age`
  decryption Secret remains cluster-local and is not a Git manifest.
- Backed up the age private key and k3s token through the private infrastructure
  repository's GitHub secret mechanism. The runtime values remain out of Git.
- Existing application repositories and their published changes remain
  separately reviewable; parent submodule pointer changes are not an
  automatic commit operation.

### 4. Replicated storage foundation

- Installed Longhorn `1.12.0` through native Flux.
- Configured a non-default `longhorn` StorageClass with three replicas and
  `Retain` reclaim policy. The existing `local-path` default was not replaced.
- Verified Longhorn managers, CSI components, engine images, instance managers,
  disks, and nodes are healthy on all three servers.
- Created, wrote to, read from, and removed a temporary three-replica Longhorn
  volume successfully.
- Pong, GoatCounter, and Dex SQLite state was restored into native Longhorn
  RWO PVCs after writer quiescence and local integrity checks. The old ACME
  `acme.json` was not copied or multi-mounted.

### 5. Application image/runtime correction

- Diagnosed the previous Caddy failure (`exec /usr/bin/caddy: operation not
  permitted`) as inherited file capabilities in the image.
- Removed the unnecessary Caddy file capability and published corrected Pong
  and portfolio image/deployment revisions:
  - Pong source/deployment: `32b6f6a` / `ec2bbe8`
  - Portfolio source/deployment: `b2ba04b` / `da677cf`
- Existing public Pong and portfolio services continued serving successfully.

### 6. Native Traefik production edge

Native Traefik runs on the two public edge servers only and serves the native
production routes. `.73` remains excluded from the edge; the former k3d
application process was retired after cutover.

- Validated the official Traefik chart `41.2.0` / Traefik `v3.7.10`.
- The staged release is a DaemonSet constrained to:
  - `.41` / `belacca-k3s-02`
  - `.42` / `belacca-k3s-03`
- Each node binds host ports 80 and 443 directly. `.73` is excluded from the
  native edge; the old k3d process has been retired.
- The native release has no ServiceLB/LoadBalancer Service and no ACME PVC;
  cert-manager issues namespace-local TLS Secrets through DNS-01.
- The container uses RuntimeDefault seccomp, a read-only root filesystem,
  privilege escalation disabled, UID 0 with only the low-port bind capability
  retained because this host-network runtime rejected non-root binding, and an
  immutable verified Traefik image index digest:
  `sha256:9c3b91d5fb7770853ca5c1124a23c34bf2d9b47ffaebeab2614cbaf410dcb2ac`.
  This exception is limited to the native Traefik DaemonSet on `.41`/`.42`.
- The DaemonSet replacement strategy was corrected to avoid host-port collision:
  `maxUnavailable: 1`, `maxSurge: 0`.
- Current native edge state:
  - HelmRepository `traefik`: `Ready=True`
  - HelmRelease `traefik`: `Ready=True`, chart `41.2.0`
  - two Traefik pods `Running/Ready`, one on each new server
  - direct HTTP and HTTPS requests to both new node IPs return the expected
    empty-router `404`
- Earlier edge errors were transient and resolved:
  1. Helm's offline render needed the Kubernetes `policy/v1` capability
     explicitly advertised.
  2. A rolling update initially tried to bind replacement host ports before
     removing old pods.
  3. The first immutable image repository value duplicated `docker.io/`.
  4. The corrected chart now reconciles successfully and both pods use the
     digest-pinned image.

The edge manifests, cert-manager boundary, native TLS, routing, application
policies, and Flux health checks are published through GitOps revision `c083165`
under:

```text
belacca-gitops/clusters/belacca-production/edge/
belacca-gitops/clusters/belacca-production/kustomization.yaml
```

Flux owns the edge, cert-manager, TLS, routing, application, and policy
Kustomizations. Native Traefik, cert-manager, Pong, portfolio, Dex, Headlamp,
Flux Web, and analytics are Ready; all application Services remain private
ClusterIP resources behind the native production edge.

### 7. Production safety checks

Repeated checks against both native production edges confirmed the expected
responses for:

- `belacca.com`
- `www.belacca.com`
- `pong.belacca.com`
- `dashboard.belacca.com`
- `flux.belacca.com`
- `stats.belacca.com`
- `francesco.belacca.com`

The following cutover actions have happened under the approved direct-DNS
fallback:

- application and API DNS records now contain `.41` and `.42` only;
- native production ingress owns public application traffic;
- Pong, GoatCounter, and Dex state was restored into new native Longhorn PVCs;
- old k3d application writers were stopped and the old Podman cluster was
  retired without deleting native PVCs or the old source manifests.

The following remain explicit follow-ups:

- Cloudflare DNS round-robin is not health-aware;
- no external backup destination or isolated external restore rehearsal exists;
- authenticated browser completion and a one-node failure drill remain;
- native Traefik UID 0 hardening review remains.

## What is being worked on now

The migration is complete. Current work is the operational SRE loop around the
native production plane: 99%/30d internal availability evidence, safe overload
boundaries, incident learning, and hardening. The 99% target has no SLA or
service credits; the separate controlled-drill recovery objective is P95 under
six minutes and remains unproven.

1. **Maintain external SLO evidence.** `belacca-status` publishes sanitized
   hourly observations and `slo.json`; 30-day values remain not reportable until
   the complete valid 720-slot window exists. Analytics SLO eligibility requires
   both `/status` and `/count`.
2. **Use native diagnostics correctly.** Native Prometheus is private diagnostic
   telemetry for Pong/Flux and does not replace external availability evidence.
   Flux notification resources are committed as a diagnostic contract, but the
   destination Secret and paging policy remain unprovisioned.
3. **Repeat isolated capacity baselines.** The disposable k3d workflow is
   manual-only, loopback-bound, serialized, bounded, and redacted. The first
   8-concurrent run hit Pong's WebSocket admission boundary before CPU/RAM
   saturation; this is not a production capacity or recovery claim.
4. **Exercise controlled recovery.** Prepare and run one-fault-at-a-time native
   edge/control-plane/storage drills only after approval, with P95-under-six-
   minute measurement and incident evidence. Do not use native production as a
   load or chaos sandbox.
5. **Externalize state recovery.** Configure encrypted off-cluster backups,
   retention, freshness/integrity alerts, and isolated restore rehearsals for
   Pong, GoatCounter, and Dex.
6. **Close failure-domain gaps.** Select a health-aware API/ingress endpoint,
   verify native NetworkPolicy enforcement, complete authenticated operator
   journeys, enforce image provenance, and review the Traefik UID 0 exception.

The former migration steps and retired-runtime procedures remain below for
historical audit context; they are not current operational instructions.

## Current problems, risks, and their status

### No active production outage

There is no known outage. The native cluster and public edges are healthy, and
public services return the expected responses through native production.

### Open migration blockers

| Item | Current status | Required decision/action |
|---|---|---|
| Stable k3s API endpoint | `k3s-api.belacca.com` resolves to native `.41`/`.42` only; kubeconfig still uses `.41` | Health-aware VIP/LB remains a hardening follow-up; direct DNS fallback is accepted for now |
| Native public ingress | Public DNS now resolves to `.41`/`.42`; both native edges serve the routes | Monitor direct-DNS round-robin behavior and retain a reviewed manual DNS removal procedure |
| ACME state | Native Cloudflare DNS-01, ClusterIssuer, and all seven Certificates are Ready | Exercise renewal/expiry handling; never multi-mount old `acme.json` |
| Native applications | Pong, portfolio, Dex, Headlamp, Flux Web, and analytics are Ready; external portfolio/Pong/analytics checks and redirect diagnostics are implemented | Complete authenticated browser journeys and native failure drills as follow-up |
| Stateful data | Pong, GoatCounter, and Dex were quiesced and restored to healthy native Longhorn RWO PVCs | Add external backup retention and repeat isolated restore rehearsal |
| Off-cluster backups | Contract/documentation exists, scheduled external backup does not | Supply object storage, encryption/KMS, retention, and restore rehearsal |
| Authenticated synthetic checks | Public redirect contracts exist; interactive login is manual | Complete browser/operator checks and add external dashboard/analytics runners |
| GitOps publication | Native root, routing, observability, notification contract, and child application pins are published and validated | Keep parent pins current and preserve Flux ownership |
| Native credential boundary | Old-production encrypted credential manifests were removed; native consumers use reviewed encrypted interfaces | Keep credential consumers and lifecycle reviewed; Cloudflare DNS-01 is active |
| State migration | Controlled local handoff completed; SQLite integrity checks and native startup passed | Externalize the artifacts and rehearse restore outside the live handoff path |

### Resolved problems

- Native `.73` join failure from inotify exhaustion: fixed with host limits.
- Documentation/recovery validator drift caused by the explicit old-production
  vocabulary: fixed while retaining the validator’s safety markers.
- Duplicate disposable/production Pong manifest paths: fixed by moving CI and
  restore rehearsal to `k8s/overlays/test/` before deleting the old monolith.
- Caddy execution failure from inherited file capabilities: fixed and images
  republished.
- Traefik Helm PDB render/API mismatch: handled by explicit Kubernetes API
  rendering and disabling the unnecessary PDB for the DaemonSet.
- Traefik host-port rolling collision: handled with `maxSurge: 0` and
  `maxUnavailable: 1`.
- Traefik digest image pull failure: fixed by using the chart's canonical
  repository value `traefik` instead of `docker.io/library/traefik`.

## Execution plan

### Phase 0 — status and ownership hygiene

- [x] Replace the obsolete broad SRE workstream plan with this migration plan.
- [x] Record the exact native cluster, public edge, DNS, Git, and workload state.
- [x] Review the local native-edge diff and run repository checks.
- [x] Publish the reviewed native-edge, TLS, routing, policy, and application
      GitOps changes; local rendering, safety scans, and live edge validation passed.
- [x] Resume native Flux against the published revision and confirm the edge,
      source, application, and protected-secret inventories reconcile without
      recreating removed credential objects.
- [x] Remove only the audited obsolete Pong child Flux tree and superseded
      historical handoff; retain active rollback, ACME, PVC, CI, restore, and
      k3d host safeguards.

### Phase 1 — API and host failure-domain readiness

- [x] Verify three-node etcd membership and node readiness.
- [x] Verify native API DNS records and certificate SANs.
- [ ] Select and provision a health-aware API VIP/L4 load balancer; direct
      Cloudflare DNS fallback is currently accepted.
- [x] Publish `k3s-api.belacca.com` with `.41` and `.42` direct A records;
      kubeconfig remains pinned to `.41` pending a health-aware endpoint.
- [ ] Test API access while stopping or isolating one server, without touching
      the old production application edge.
- [ ] Decide whether to enable SSH hardening on `.73` before cutover and define
      a tested recovery path.

### Phase 2 — Native edge, TLS, and routing

- [x] Validate pinned Traefik chart and immutable image.
- [x] Validate direct native HTTP/HTTPS listeners on both new nodes.
- [x] Publish and adopt the Traefik HelmRelease through Flux. GitOps revision
      `c083165` contains the reviewed edge/TLS/routing state, and the live
      release is Flux-owned and Ready.
- [x] Stage the cert-manager `v1.21.1` controller and CRDs through Flux with
      immutable images, bounded resources, retained CRDs, and no ACME consumer.
- [x] Use cert-manager DNS-01 plus namespace-local TLS Secrets; the old
      shared RWO `acme.json` is not mounted into native Traefik.
- [x] Stage TLS certificates and DNS-01 resources without changing public records.
- [x] Deploy native route Ingresses for portfolio, Pong, analytics, Dex,
      Headlamp, and Flux UI.
- [x] Test routes with direct node IPs/SNI on both native edge nodes; public DNS
      remains unchanged.

### Phase 3 — Workload and data migration

- [x] Create the native Pong/portfolio namespaces and Flux child
      Kustomizations after the native context, Longhorn health, and publication
      gates passed.
- [x] Deploy native production portfolio, Pong, Dex, Headlamp, analytics, and
      Flux UI workloads with encrypted credential interfaces, TLS, routes, and
      policy boundaries.
- [x] Create the native Pong Longhorn-backed RWO PVC with explicit prune/keep
      protection and verify its healthy three-replica volume; other stateful
      target PVC contracts remain pending.
- [x] Quiesce and copy Pong, GoatCounter, and Dex SQLite state, run integrity
      checks, and restore into native Longhorn RWO PVCs.
- [x] Verify restored databases by native startup, file checks, and functional
      routes; external backup retention remains a follow-up.
- [x] Run private native startup/readiness, origin, WebSocket, disposable-room,
      cleanup, portfolio, and route-exposure tests; authenticated operator and
      analytics tests remain deferred.

### Phase 4 — Cutover and rollback validation

- [x] Validate direct native hostnames, redirects, TLS SANs, edge listeners,
      analytics redirect/collector reachability, dashboard redirect, and Flux
      reconciliation on both native edge nodes.
- [x] Complete native Pong WebSocket regression, OIDC discovery/redirect,
      and analytics collector checks. Full authenticated browser completion
      remains a follow-up.
- [x] Establish a bounded cutover window with old and native paths observable.
- [x] Change only the approved Cloudflare DNS records to native `.41`/`.42`.
- [x] Verify native application health and user journeys repeatedly after cutover.
- [ ] Exercise one-server failure and confirm etcd/API, edge, replicated storage,
      and application recovery expectations.
- [x] Stop the old k3d writers and retire its Podman containers after the native
      cutover; retain source manifests and native rollback documentation.

### Phase 5 — Operational completion

- [ ] Configure encrypted off-cluster backups with retention, RPO/RTO, and
      restore alerts.
- [ ] Complete a real isolated restore rehearsal using a copied database.
- [ ] Complete authenticated dashboard and analytics synthetic runners.
- [ ] Configure Flux notification destination credentials out of band.
- [x] Update infrastructure, GitOps, Pong, portfolio, and workspace
      documentation with the native-production/retired-old-production vocabulary.
- [x] Update service inventory and final migration evidence after workloads
      and data were migrated.
- [x] Retire the old k3d Podman cluster after the approved native cutover;
      retain Git history and native post-cutover procedures.

## Current working tree and runtime references

### Runtime references

```text
Native kubeconfig: /root/.kube/belacca-native
Native API DNS:    k3s-api.belacca.com:6443
Native cluster:    three Ready embedded-etcd servers
Retired old k3d:    k3d-pong on .73; native DNS cutover complete
```

### Repository state

- `/root/sources/belacca-infrastructure`: published native host safeguards and
  security-boundary documentation; external backup, API failover, and node
  failure rehearsal remain unproven.
- `/root/sources/belacca-platform`: current parent commit pins all reviewed
  child documentation, SLO, observability, notification, telemetry, and
  capacity changes.
- `/root/sources/belacca-platform/belacca-gitops`: native root, routing,
  private observability, notification contract, catalog, and current production
  docs are published; the destination Secret and paging policy remain absent.
- `cloudnativepong`: native runtime, external SLO journey contract, bounded
  telemetry, guarded disposable capacity workflow, and redacted evidence path
  are published; the 8-concurrent baseline hit WebSocket admission before
  resource saturation.
- `francesco-belacca-site`: public project descriptions and reliability/status
  documentation describe the current evidence boundaries and unproven gaps.
- `belacca-status`: hourly external checks and sanitized 99%/30d SLO evidence
  are published; values remain non-reportable until the complete valid window.
- No passwords, tokens, private keys, plaintext Secret values, database files,
  or generated private telemetry belong in this plan.

## Completion criteria

The public cutover is complete when the following are true; remaining
hardening is tracked separately:

1. Native Traefik/TLS/routing is GitOps-owned and serves all required hosts.
2. Pong, GoatCounter, and Dex state is restored with integrity on Longhorn RWO
   PVCs, preserving SQLite single-writer behavior.
3. Cloudflare application/API DNS records resolve to native `.41`/`.42` only.
4. Public native probes, Pong WebSocket journeys, analytics collector paths,
   and OIDC discovery/redirects pass on both edges.

Post-cutover hardening remains:

5. Health-aware API/ingress failover.
6. Encrypted external backups and isolated restore rehearsal.
7. Authenticated browser journeys and one-node failure drill.
8. Native Traefik UID 0 hardening review.
