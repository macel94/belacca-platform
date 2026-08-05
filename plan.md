# Belacca Platform SRE Improvement Plan

> Resumable execution plan for `belacca-platform`.
>
> Last updated: 2026-08-05
> Coordinator: primary pi session
> Agent model policy: all delegated agents must use `openai/gpt-5.6-luna`.
> Git policy: do not stage or commit automatically; review nested repositories and parent gitlinks separately.

## Resume protocol

1. Read this file from top to bottom.
2. Inspect `git status --short --branch` in the parent and each nested repository.
3. Check the **Verification log** and **Final coordinator state** before changing code.
4. Continue with the first unchecked item whose prerequisites are satisfied.
5. After every valuable, verified capability:
   - run the narrowest relevant tests;
   - update the owning repository documentation;
   - update this file with the implementation, verification, and follow-up;
   - do not claim completion from manifest rendering alone when cluster validation is required.
6. Never delete or recreate the existing `k3d-pong` cluster or protected PVCs.
7. Never commit secrets, tokens, private telemetry, or credentials.

## Scope and success criteria

Implement the practical SRE improvements proposed for:

- `pong.belacca.com` / `cloudnativepong/`: abuse resistance, user-facing telemetry, resilience tests, room isolation, and delivery provenance.
- `francesco.belacca.com` / `francesco-belacca-site/`: public reliability documentation/status experience, security/performance verification, and generated operational metadata where safe.
- `belacca-gitops/`: SLO/incident integration, observability plumbing, Flux notifications, network isolation, workload disruption policy, backup/restore automation, supply-chain verification, and service catalog metadata.
- Parent workspace: repeatable validation, documentation synchronization, and resume-friendly operational tooling.

The target is not merely more Kubernetes resources. The target loop is:

```text
user journey -> SLI -> SLO -> error budget/alert -> incident evidence -> tested recovery
```

## Workstreams

### A. Baseline and contracts

- [x] Inventory current repositories, workloads, public endpoints, CI, Flux, security controls, and stateful data.
- [x] Research current SRE/platform trends and primary guidance (SLOs, burn-rate alerting, OpenTelemetry, Flux notifications, SLSA/Sigstore, Kubernetes resilience).
- [x] Add a validated platform service catalog with service owner, public host, tier, dependencies, SLO, RTO, RPO, dashboard, and runbook fields. (Catalog validator and Kustomize/JSON validation pass.)
- [x] Define practical initial SLOs/SLIs for portfolio, Pong lobby, Pong game sessions, analytics, and dashboard. (Initial targets and proposed/measured status are documented; no item is claimed measured without telemetry.)
- [x] Document the current single-host/node-local-storage failure domain and the intentional single-writer SQLite boundary. (GitOps reliability docs and catalog metadata are updated.)

### B. Pong application reliability and abuse resistance (`cloudnativepong/`)

- [x] Validate WebSocket `Origin` against an explicit production/local allowlist; add tests. (Production and local origins are configured separately; exact normalization/rejection tests pass.)
- [x] Add bounded request bodies, HTTP server timeouts, method/content validation, and correct error status codes. (Strict bounded JSON decoding, status mapping, and server timeouts implemented and tested.)
- [x] Add per-client rate/concurrency limits for room creation, joins, HTTP, and WebSocket sessions; expose safe configuration. (Bounded in-process admission with safe positive environment overrides and limiter tests implemented.)
- [x] Add application metrics for HTTP, rooms, room lifecycle, Pod orchestration, SQLite, WebSockets, admission, callbacks, and cleanup. (Fixed-name counters/gauges are integrated without labels/high-cardinality values; tests pass.)
- [x] Add a minimal `/metrics` endpoint with bounded labels and document the scrape contract. (Dependency-free Prometheus exposition with no labels and regression tests implemented.)
- [x] Add trace/request correlation IDs without logging names, IPs, tokens, or room contents. (Opaque validated IDs, response/callback propagation, and safe logging scrub are tested.)
- [x] Harden dynamic room Pods: non-root, no token, no privilege escalation, dropped capabilities, read-only root, and RuntimeDefault seccomp in generated and checked-in templates. (Digest pinning and full network policy remain open.)
- [x] Add room lifecycle and failure-injection tests: restart, missing callback, orphan cleanup, quota/admission rejection, Pod failure, and cleanup retry behavior. (Dependency-injected orchestration tests pass.)
- [x] Add load/smoke tooling for room creation, join, WebSockets, cleanup latency, and resource ceilings. (Bounded aggregate-only harness plus local HTTP/origin and two-player synthetic passed; sustained public load remains external.)
- [x] Reconcile Pong operational documentation with each verified implementation. (README, DEPLOYMENT, and HANDOFF document telemetry, admission, origins, provenance, synthetic, recovery, and current limitations.)

### C. Observability and SLO enforcement (`belacca-gitops/` plus applications)

- [x] Choose a deliberately small observability stack appropriate for one k3d host. (Staged plain Prometheus v3.13.2, one replica, private ClusterIP, 7-day/2 GB ephemeral retention; no heavyweight Operator/CRD dependency.)
- [x] Add Prometheus-compatible collection for application metrics and Kubernetes/Flux state. (Pinned Prometheus manifest, static Pong/Flux scrape config, bounded sample limits, and private network policy render; collector is staged but not yet reconciled.)
- [x] Add OpenTelemetry Collector and at least one end-to-end Pong trace path, or document a tested staged implementation if cluster constraints prevent rollout. (Pong now emits opt-in OTLP/HTTP spans with W3C propagation through HTTP, room callbacks, and proxy WebSockets; no collector is claimed deployed.)
- [x] Add blackbox/external synthetic checks for all public services and the Pong create/join/WebSocket workflow. (Out-of-band Pong workflow plus machine-readable portfolio/Pong/analytics/dashboard contracts and unknown-by-default public status are implemented.)
- [x] Add SLO recording/alert rules and multi-window burn-rate alerts; avoid paging on symptoms that do not consume meaningful budget. (Nine proposed recording/alert rules validate with official promtool; runtime measurement/destination remains open.)
- [x] Add dashboards for user journeys, deployment health, room lifecycle, node capacity, storage, certificates, and Flux reconciliation. (Private staged dashboard JSON/query source is validated; Grafana installation and live panels remain open.)
- [x] Add Flux notifications for source/Kustomization/Helm failures and successful deployment status. (Provider/Alert resources render and server-side dry-run; destination Secret remains intentionally out of band.)
- [x] Keep telemetry retention, cardinality, and privacy controls explicit. (Pong metrics have no labels; GitOps docs state proposed SLO/telemetry status and external prerequisites.)
- [x] Reconcile GitOps and runbook documentation after each deployed capability. (README, cluster README, migration, subdomain, notifications, and reliability docs updated.)

### D. GitOps security and resilience (`belacca-gitops/`)

- [x] Add default-deny NetworkPolicies and least-privilege allow rules for portfolio, Pong, analytics, Headlamp/OAuth, and observability. (Scoped policies render and pass server-side dry-run; runtime CNI connectivity validation remains.)
- [x] Add PodDisruptionBudgets and topology spread/anti-affinity only where they reflect real replicas and the three-node topology. (PDBs added only for confirmed two-replica workloads; topology spread remains follow-up.)
- [x] Add startup/readiness/liveness probe review; do not use liveness checks that can amplify outages. (Startup probes added to Pong gateway/static/API, CI manifest copies, and portfolio; existing liveness checks remain bounded.)
- [ ] Add encrypted off-cluster backups for Pong and GoatCounter with retention and explicit RPO/RTO. (External storage/key prerequisites remain unresolved.)
- [x] Add a restore verification job/process in an ephemeral k3d environment; prove application startup and synthetic workflows after restore. (SQLite online-backup/restore self-test and fail-closed isolated runner/dry-run are validated; real disposable-cluster run remains prerequisite dependent.)
- [x] Add controlled game-day/failure tests to CI or a documented operator workflow. (Bounded gateway/static/API/room/Flux/NetworkPolicy drills documented and recovery contract validated.)
- [x] Finish the Flux ownership migration safely and enable root pruning only after inventory and protected-state verification. (Root `prune: true` is published in the GitOps tree after live root-inventory coverage, disjoint child inventories, Ready children, public route checks, and protected state verification; the staged observability child remains `prune: false`.)
- [x] Reconcile DNS/ACME documentation with the actual committed DNS-01 Traefik configuration. (GitOps docs now describe Cloudflare DNS-01 and the real Secret key contract.)

### E. Software supply chain and delivery (`cloudnativepong/`, `francesco-belacca-site/`, `belacca-gitops/`)

- [x] Generate SBOMs for every published image. (BuildKit publish workflows request SBOM attestations; release metadata/docs make registry resolution explicit.)
- [x] Scan images and fail on an explicitly documented severity policy. (Trivy HIGH/CRITICAL report-only default plus manual strict gate are implemented and documented.)
- [ ] Sign images with keyless Cosign and publish SLSA/in-toto provenance. (Provenance/SBOM generation and manual Cosign hooks exist; actual registry/OIDC signing remains external.)
- [x] Deploy immutable image digests and verify provenance/signatures before reconciliation where the cluster supports it. (Digest-only promotion/validation contract is implemented; live Flux/admission signature enforcement remains open.)
- [x] Add a promotion gate from ephemeral integration validation to production image digest. (Release metadata validator runs in CI; digest promotion helper requires four exact GHCR digests and rejects mutable tags.)
- [x] Preserve rollback metadata and connect deployments to source commits and Flux health. (Release metadata, source commit/tag contract, Flux runbooks, and rollback docs are committed.)

### F. Portfolio reliability experience (`francesco-belacca-site/`)

- [x] Add a public reliability/systems page that explains SLOs, architecture, delivery, backups, security boundaries, and incident practice without exposing secrets or infrastructure-sensitive details. (Static `/reliability.html` added; current versus planned capabilities are labeled.)
- [x] Add a status surface backed by externally generated, sanitized status data; do not make the cluster the only source of its own status page. (Unknown-by-default `/status.html` + schema/contract + no-store artifact are shipped; external publisher remains a prerequisite.)
- [x] Add version/build/deployment metadata safely and verify cache behavior. (Short build SHA substitution and cache/header checks verified with Podman.)
- [x] Add automated accessibility, security-header, performance-budget, and link/redirect tests. (Static semantic/security/link checks and npm suite pass; external performance budget remains follow-up.)
- [x] Reconcile site README and public copy with actual deployed capabilities after verification. (README, privacy, discovery assets, sitemap, and page copy updated; runtime deployment verification remains pending.)

### G. Bounded AI-assisted operations

- [x] Build a read-only incident evidence bundle or assistant input format from SLO status, Flux events, Kubernetes events, recent logs, deployment revisions, and runbooks. (Allowlisted, bounded `scripts/incident_evidence.py` collector emits JSON/Markdown evidence bundles.)
- [x] Require evidence references, confidence, and human approval for any proposed action. (Bundle schema and documentation include source references, confidence, and pending human approval fields.)
- [x] Never allow the assistant to mutate the cluster directly; changes must be reviewed GitOps commits/PRs. (Collector has read-only command allowlists and the contract requires GitOps-only changes.)
- [x] Document data minimization and secret redaction. (Secret/token/password/JWT/private-key/IP-like redaction is tested.)

## Delegation plan

Delegated work must be isolated by repository/files and launched in tmux with:

```bash
pi --provider openrouter --model openai/gpt-5.6-luna '<task>'
```

Current intended parallel tracks:

1. Pong telemetry, lifecycle metrics, correlation IDs, and failure tests (`pong-telemetry`).
2. Resource-conscious Prometheus-compatible observability, SLO rules, dashboards, and synthetic contracts (`observability-slos`).
3. Safe isolated restore rehearsal, backup contract, and game-day runbooks (`recovery-gameday`).
4. Read-only incident evidence bundle, bounded AI-assistance contract, and truthful external status surface (`incident-status`).

Completed first-wave tracks remain documented in the verification log; stop completed agents before starting overlapping edits.

Agents must not stage or commit. They must report changed paths, tests run, unresolved prerequisites, and documentation updates. The coordinator owns integration, cross-repository validation, plan updates, and final verification.

## Verification gates

### Local gates

- [x] `make site-test`
- [x] `make pong-test`
- [x] `make manifests`
- [x] `make validate`
- [x] nested repository `git diff --check`
- [x] YAML/Kustomize rendering and policy validation
- [x] tests for every new security/reliability behavior

### Runtime gates (only when cluster access is safe and available)

- [x] `kubectl config current-context` is `k3d-pong` before diagnostics. (Final read-only check confirmed it.)
- [x] no destructive cluster/PVC operation. (No cluster/PVC mutation, deletion, staging, or commit was performed.)
- [x] Flux sources/Kustomizations/HelmReleases are Ready. (Final read-only check confirmed existing application sources/Kustomizations and workloads; staged observability was not reconciled.)
- [x] public health, redirect, certificate, and synthetic user journeys pass. (Public health/homepage/Pong/analytics checks and redirect passed; local two-player synthetic passed. Public status artifact remains old until publication.)
- [ ] backup restore passes in an isolated environment. (Self-test and dry-run pass; real disposable k3d rehearsal requires Docker/k3d/images and an operator-approved copied database.)
- [x] no credentials or private data appear in logs, artifacts, metrics, or Git. (Safety scans passed after removing generated caches; only intentional `${{ secrets.GITHUB_TOKEN }}` references and interactive prompt documentation remain.)

## Verification log

- 2026-08-05: Current public checks returned HTTP 200 for portfolio health/homepage, Pong homepage, and GoatCounter status. One portfolio health request was slow (~5s), so repeated external measurement is required before drawing conclusions.
- 2026-08-05: Confirmed current platform already has Flux, immutable SHA image tags, CI, probes, HPA, protected PVCs, OAuth2 Headlamp, security headers, and runbooks.
- 2026-08-05: Initial gaps were confirmed and addressed where locally verifiable: application metrics/SLO groundwork, Flux Alert/Provider resources, Pong abuse boundaries, origin policy, dynamic Pod hardening, and DNS-01 documentation are now implemented or staged; external backup/status/runtime enforcement remain open.
- 2026-08-05: Portfolio agent added `/reliability.html`, safe short build metadata, security/header/cache tests, updated site documentation/discovery assets, and verified npm/static checks plus Podman container smoke test.
- 2026-08-05: Delivery agent added dependency-light synthetic and SQLite backup/restore tooling; local two-player Pong synthetic and SQLite round-trip self-test passed. Supply-chain workflow/hooks are present but require final review and runtime registry/OIDC verification.
- 2026-08-05: GitOps agent added service catalog/validation, reliability/notification documentation, Flux notification resources, scoped NetworkPolicies, and PDBs. All nested Kustomizations rendered, catalog validation passed, whitespace/credential scans passed, and server-side dry-runs passed; runtime CNI/Secret prerequisites remain.
- 2026-08-05: Pong hardening batch verified: Go unit/race/vet pass; exact origin policy, bounded JSON/status handling, admission limits, server timeouts, aggregate metrics, local HTTP/origin smoke, two-player synthetic, and hardened room templates all pass.
- 2026-08-05: Pong telemetry batch stabilized: room/SQLite/HTTP/WebSocket/admission/callback metrics, opaque request IDs, injected orchestration failures, bounded aggregate load smoke, and documentation updates pass unit/race/vet plus eight repeated full-suite runs.
- 2026-08-05: Staged observability batch independently verified: plain Prometheus v3.13.2 digest-pinned manifests, private network policy, bounded retention/sample limits, static Pong/Flux scrape config, nine proposed rules, synthetic/dashboard JSON contracts, and official promtool config/rule validation pass. No observability resources have been reconciled to the live cluster.
- 2026-08-05: Optional OpenTelemetry tracing follow-up verified: Go OTel SDK/exporter `v1.45.0`, no-endpoint no-op behavior, W3C propagation, bounded route normalization, HTTP/callback/WebSocket integration, Go unit/race/vet, build, and local two-player synthetic all pass. Collector deployment remains an external/runtime prerequisite.
- 2026-08-05: OTel follow-up committed in `cloudnativepong` as `6544842`; parent pointer was updated in the subsequent parent commit.
- 2026-08-05: Immutable release follow-up committed in `cloudnativepong` as `22929c7`: release metadata validator, digest-only promotion helper, CI contract checks, and docs pass Go/race/vet plus mutable-reference rejection.
- 2026-08-05: Final coordinator runtime read-only check confirmed context `k3d-pong`, three Ready nodes, Flux application sources/Kustomizations Ready, existing workloads Running, and no `observability` workload deployed because changes remain uncommitted/unpublished.
- 2026-08-05: Flux ownership migration safety gates passed: the checked-in root render contains every live root-inventory object, application/routing child inventories are disjoint and Ready, public route checks passed, and Pong/analytics/ACME stateful resources are present with prune protection (Pong PV reclaim policy `Retain`). Root `prune: true` is now published in the GitOps tree; it still requires live reconciliation.
- 2026-08-05: Incident/status batch independently verified: 4 Python evidence tests, 16 site tests, Python/Node/shell syntax checks, safe-failure collection, redaction tests, unknown-by-default status contract, and no-store status packaging pass. External status publication remains intentionally unconfigured.
- 2026-08-05: Recovery/game-day batch added an opt-in isolated `pong-restore-*` rehearsal, backup/object-storage/encryption contract, and bounded failure drills; backup/rehearsal self-tests and dry-run safety checks pass. Real k3d rehearsal remains runtime/dependency dependent.

## Final coordinator state

- All delegated agents are stopped; no tmux work remains active.
- Parent and nested repositories contain local commits for the implemented work; the pre-existing empty `cloudnativepong/oom` file remains intentionally untracked and uncommitted.
- Local implementation is complete for Pong hardening/telemetry, site reliability/status UX, incident evidence, GitOps catalog/policies/notifications, staged Prometheus observability, recovery/game-day contracts, and supply-chain/release hooks.
- The staged observability child is intentionally not live: reconcile it only after reviewing host resource budget, CNI policy behavior, Prometheus target health, and its existing `prune: false` ownership decision.
- The public site status page is intentionally unknown/not configured until an external publisher supplies reviewed, timestamped, sanitized data.
- Runtime gates remain open for external notification credentials, off-cluster backup storage/KMS, real isolated restore, public synthetic scheduling variables, image signing/digest enforcement, measured SLOs/burn-rate paging, and live reconciliation of the newly enabled root pruning.

## Deferred/external prerequisites

These require operator-owned infrastructure or secrets and must not be faked in Git:

- publish/review child repository changes and update the parent submodule pointers;
- external synthetic monitor account/status publisher and repository variables;
- notification destination tokens and the `platform-notification-webhook` Secret;
- object-storage credentials, bucket policy, retention/WORM, and encryption/KMS keys;
- Google OAuth, GoatCounter admin, and Cloudflare DNS-01 Secrets;
- registry/OIDC execution for Cosign signing and policy enforcement by digest;
- real disposable-k3d restore rehearsal prerequisites (Docker/k3d, local images, copied SQLite artifact);
- measured SLO data, alert destination, incident paging policy, and public status publication;
- live reconciliation of the root-pruning change and any irreversible pruning or stateful-resource deletion.
