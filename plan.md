# Belacca native k3s migration — status and execution plan

**Status date:** 2026-08-07 19:12 CEST
**Scope:** migrate the live single-host `k3d-pong` platform on `.73` to a
three-server native k3s HA cluster without deleting or casually recreating
workloads, PVCs, or the current production edge.

## Executive status

The native platform foundation is healthy and the migration is proceeding as a
staged blue/green build. The three-server native k3s cluster, embedded etcd,
Flux, SOPS/age, Longhorn, cert-manager controller/CRDs, and a stateless native
Traefik edge have all been validated. The original k3d cluster on `.73` is still the active production
cluster and still owns public application traffic on ports 80/443.

**No public application DNS, ingress ownership, production data, or protected
production PVC has been cut over.** Private route-less Pong and portfolio
staging workloads are live on native ClusterIP Services; existing public
services remain available and returned HTTP 200 during the native work.

Overall state: **healthy staging foundation; migration not yet complete.**

## This continuation’s completed work

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
  cluster documentation with the explicit active-public/native-staging model.
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
  `83c663b`. The native edge, cert-manager, and both route-less application
  Kustomizations are Flux-owned and Ready: Pong is at `958a0ad`, and portfolio
  is at generated deployment revision `15808ea`. Their private staging
  workloads are live; no public route or production-state ownership has been
  introduced.
- Removed old-production OAuth, Cloudflare, analytics-admin, and proxy Secret
  manifests from native staging. Native Git now contains namespace declarations
  only under `secrets/`; the out-of-band `flux-system/sops-age` decryption
  Secret remains cluster-local and is not a Git manifest.
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
- No Pong, GoatCounter, Dex, or ACME production data has been restored into
  native Longhorn yet.

### 5. Application image/runtime correction

- Diagnosed the previous Caddy failure (`exec /usr/bin/caddy: operation not
  permitted`) as inherited file capabilities in the image.
- Removed the unnecessary Caddy file capability and published corrected Pong
  and portfolio image/deployment revisions:
  - Pong source/deployment: `32b6f6a` / `ec2bbe8`
  - Portfolio source/deployment: `b2ba04b` / `da677cf`
- Existing public Pong and portfolio services continued serving successfully.

### 6. Native Traefik edge staging

A native edge has been staged on the two new servers only. It is intentionally
not serving application routes yet.

- Validated the official Traefik chart `41.2.0` / Traefik `v3.7.10`.
- The staged release is a DaemonSet constrained to:
  - `.41` / `belacca-k3s-02`
  - `.42` / `belacca-k3s-03`
- Each node binds host ports 80 and 443 directly. `.73` is excluded, so the
  old k3d process remains the only public edge on the existing host.
- The native release has no ServiceLB/LoadBalancer Service, no ACME PVC, and no
  application route yet.
- The container runs non-root with RuntimeDefault seccomp, read-only root
  filesystem, privilege escalation disabled, all capabilities dropped except
  `NET_BIND_SERVICE`, and an immutable verified Traefik image index digest:
  `sha256:9c3b91d5fb7770853ca5c1124a23c34bf2d9b47ffaebeab2614cbaf410dcb2ac`.
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

The edge manifests, cert-manager controller boundary, and native Flux health
checks are published in GitOps commit `83c663b` under:

```text
belacca-gitops/clusters/belacca-production/edge/
belacca-gitops/clusters/belacca-production/kustomization.yaml
```

Flux owns the edge, cert-manager controller, and route-less application
Kustomizations. Native Traefik, cert-manager, Pong, and portfolio staging are
Ready; all application Services remain private ClusterIP resources with no
public route, issued application certificate, or production-state ownership.

### 7. Production safety checks

Repeated checks during staging confirmed HTTP 200 for:

- `belacca.com`
- `www.belacca.com`
- `pong.belacca.com`
- `dashboard.belacca.com`
- `flux.belacca.com`
- `stats.belacca.com`
- `francesco.belacca.com`

The following have **not** happened:

- no public application DNS change;
- no public load balancer change;
- no deletion or recreation of `k3d-pong`;
- no deletion of protected application, analytics, Dex, or ACME PVCs;
- no native application-data restore;
- no production ingress ownership switch.

## What is being worked on now

The immediate work is to turn the validated native edge into a complete,
GitOps-owned, application-capable migration target without affecting the old
production edge.

1. **Finish native edge/TLS ownership.** The Traefik and cert-manager
   controller boundaries are Flux-owned. Next, review the DNS-01 credential,
   Issuer, certificate Secret, and route ownership design without exposing
   production ACME state or changing public DNS.
2. **Choose the stable k3s API endpoint.** Determine whether the VPS provider
   supplies a floating IP or TCP load balancer. Prefer that endpoint for
   `k3s-api.belacca.com:6443`; the current three-A-record arrangement is only a
   fallback and is not a health-aware API load balancer.
3. **Finish native TLS/ACME design.** The old ACME data is a single-writer
   `ReadWriteOnce` volume. It must not simply be mounted into two Traefik pods.
   Choose and test either a safe single-writer arrangement or a DNS-01
   certificate-management design that produces a Kubernetes TLS Secret for
   both edge nodes.
4. **Stage native routing without public DNS changes.** Deploy the application
   namespaces, services, routes, dashboard access, Dex, and TLS resources in
   native GitOps. Validate them through direct node IPs/temporary host headers.
5. **Migrate state safely.** Take verified external copies of Pong and GoatCounter
   SQLite data, restore into Longhorn-backed single-writer PVCs, and validate
   application startup and data integrity before any public cutover.
6. **Run the native application test matrix.** Validate Pong create/join/
   WebSocket behavior, portfolio health, analytics collector paths, Dex/OIDC,
   Headlamp, Flux UI, certificates, redirects, NetworkPolicies, and rollback.
7. **Cut over only after a review gate.** Move public ingress/API traffic through
   the selected load balancer/DNS strategy, monitor the old and new paths in
   parallel, and retain the k3d rollback path until the post-cutover checks
   pass.

## Current problems, risks, and their status

### No active production outage

There is no known outage. The native cluster is healthy, the staged edge is
healthy, and public services remain HTTP 200 through the old k3d edge.

### Open migration blockers

| Item | Current status | Required decision/action |
|---|---|---|
| Stable k3s API endpoint | DNS name resolves to three A records; kubeconfig still uses `.41` | Confirm provider floating IP or TCP LB, then switch and failure-test the endpoint |
| Native public ingress | Direct listeners and Flux-owned route-less edge work on `.41`/`.42`; no public routes | Choose TLS/ACME, stage reviewed routes, and validate before DNS cutover |
| ACME state | cert-manager controller/CRDs are Ready; no Issuer, Certificate, DNS solver, credential, or certificate state exists | Add only a reviewed Cloudflare DNS-01 Secret/Issuer/Certificate contract; never multi-mount old `acme.json` |
| Native applications | Route-less Pong/portfolio Kustomizations are Ready; private workloads and Longhorn Pong PVC are live | Run private functional tests, then add reviewed routing only after TLS/state gates |
| Stateful data | Existing data remains on old k3d/local-path PVCs | Back up, restore to Longhorn, verify, and preserve single-writer SQLite |
| Off-cluster backups | Contract/documentation exists, scheduled external backup does not | Supply object storage, encryption/KMS, retention, and restore rehearsal |
| Authenticated synthetic checks | Public redirect contracts exist; interactive login is manual | Complete browser/operator checks and add external dashboard/analytics runners |
| GitOps publication | Infrastructure, Pong, portfolio, and GitOps child commits are published; native root/edge/application inventories are Ready | Keep parent pins current and preserve Flux ownership during route/state work |
| Native staging credentials | Old-production encrypted credential manifests were removed; cert-manager has only generated internal CA/Helm Secrets | Add only explicitly staging-scoped credentials with a reviewed consumer/lifecycle; Cloudflare DNS-01 remains blocked |
| State migration | Read-only audit disposition is NO-GO; no target PVCs or verified artifacts exist | Establish native context/Longhorn evidence, target contracts, quiescence, integrity-checked backups, and restore rehearsal |

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
- [x] Publish the reviewed native-edge and route-less application GitOps
      changes; local rendering, safety scans, and live edge validation passed.
- [x] Resume native Flux against the published revision and confirm the edge,
      source, application, and protected-secret inventories reconcile without
      recreating removed credential objects.
- [x] Remove only the audited obsolete Pong child Flux tree and superseded
      historical handoff; retain active rollback, ACME, PVC, CI, restore, and
      k3d host safeguards.

### Phase 1 — API and host failure-domain readiness

- [x] Verify three-node etcd membership and node readiness.
- [x] Verify native API DNS records and certificate SANs.
- [ ] Select and provision the recommended single Contabo floating VIP with
      fenced active/passive failover for `:6443`, or validate a managed L4/TCP
      load-balancer alternative.
- [ ] Put the stable endpoint in infrastructure inventory and kubeconfig.
- [ ] Test API access while stopping or isolating one server, without touching
      the old production application edge.
- [ ] Decide whether to enable SSH hardening on `.73` before cutover and define
      a tested recovery path.

### Phase 2 — Native edge, TLS, and routing

- [x] Validate pinned Traefik chart and immutable image.
- [x] Validate direct native HTTP/HTTPS listeners on both new nodes.
- [x] Publish and adopt the Traefik HelmRelease through Flux. GitOps commit
      `83c663b` contains the reviewed HelmRepository/HelmRelease, and the live
      release is Flux-owned and Ready.
- [x] Stage the cert-manager `v1.21.1` controller and CRDs through Flux with
      immutable images, bounded resources, retained CRDs, and no ACME consumer.
- [ ] Choose the ACME/certificate state architecture for two edge nodes.
      Current recommendation: cert-manager DNS-01 plus namespace-local TLS
      Secrets; do not use the old shared RWO `acme.json` design.
- [ ] Stage TLS certificates and DNS-01 renewal without changing public records.
- [ ] Deploy native route CRs/Ingresses for portfolio, Pong, analytics, Dex,
      Headlamp, and Flux UI.
- [ ] Test routes with direct node IPs and temporary host headers.

### Phase 3 — Workload and data migration

- [x] Create the native Pong/portfolio namespaces and route-less Flux child
      Kustomizations after the native context, Longhorn health, and publication
      gates passed.
- [x] Deploy private route-less portfolio and Pong gateway/static/API staging
      workloads; Dex, Headlamp, analytics, and Flux UI remain deferred until
      their own secrets, routes, and state contracts are reviewed.
- [x] Create the native Pong Longhorn-backed RWO PVC with explicit prune/keep
      protection and verify its healthy three-replica volume; other stateful
      target PVC contracts remain pending.
- [ ] Produce verified copies of existing Pong, GoatCounter, Dex, and required
      ACME/application state outside the old cluster. This remains explicitly
      NO-GO until quiescence and integrity/restore evidence exist.
- [ ] Restore and checksum/validate SQLite data in native PVCs.
- [x] Run private native startup/readiness, origin, WebSocket, disposable-room,
      cleanup, portfolio, and route-exposure tests; authenticated operator and
      analytics tests remain deferred.

### Phase 4 — Cutover and rollback validation

- [ ] Validate all public hostnames, redirects, TLS SANs, WebSockets, analytics
      paths, dashboard access, and Flux reconciliation on native edge.
- [ ] Establish a monitoring window with old k3d and native paths observable.
- [ ] Change only the approved load balancer/DNS records.
- [ ] Verify application health and user journeys repeatedly after cutover.
- [ ] Exercise one-server failure and confirm etcd/API, edge, replicated storage,
      and application recovery expectations.
- [ ] Keep the old k3d cluster and protected PVCs intact until the rollback window
      closes and the data-retention decision is reviewed.

### Phase 5 — Operational completion

- [ ] Configure encrypted off-cluster backups with retention, RPO/RTO, and
      restore alerts.
- [ ] Complete a real isolated restore rehearsal using a copied database.
- [ ] Complete authenticated dashboard and analytics synthetic runners.
- [ ] Configure Flux notification destination credentials out of band.
- [x] Update infrastructure, GitOps, Pong, portfolio, and workspace
      documentation with the active-public/native-staging vocabulary.
- [ ] Update service inventory and final migration evidence after workloads and
      data are actually migrated.
- [ ] Only then decide whether the old k3d cluster can be retired.

## Current working tree and runtime references

### Runtime references

```text
Native kubeconfig: /root/.kube/belacca-native
Native API DNS:    k3s-api.belacca.com:6443
Native cluster:    three Ready embedded-etcd servers
Old production:    k3d-pong on .73, still serving public traffic
```

### Repository state

- `/root/sources/belacca-infrastructure`: published safeguards/documentation
  and cert-manager-boundary documentation at commit `7a61b86`.
- `/root/sources/belacca-platform`: parent documentation and child gitlink
  state is published at the current parent commit.
- `/root/sources/belacca-platform/belacca-gitops`: published native root,
  edge, cert-manager controller/CRD, source, application, and
  credential-boundary state at `83c663b`; Flux reconciliation is Ready.
- `cloudnativepong`: published native-staging and cleanup state at `958a0ad`.
- `francesco-belacca-site`: published documentation and generated deployment
  state at `15808ea`.
- No passwords, tokens, private keys, plaintext Secret values, database files,
  or generated private telemetry belong in this plan.

## Completion criteria

The migration is complete only when all of the following are true:

1. Three-server native k3s/etcd survives a one-server failure test.
2. A stable health-aware API endpoint is selected and tested.
3. Native Traefik/TLS/routing is GitOps-owned and serves all required hosts.
4. Pong, GoatCounter, Dex, and other stateful data are backed up and restored
   with verified integrity on Longhorn-backed PVCs.
5. SQLite workloads remain single-writer unless their architecture is changed.
6. Public DNS/traffic cutover passes repeated application and authentication
   journeys with a documented rollback path.
7. Encrypted off-cluster backups and an isolated restore rehearsal pass.
8. The old k3d rollback environment is retained until the final approval gate.
