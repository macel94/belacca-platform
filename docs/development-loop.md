# Fast development loop

This workspace uses GitOps for production delivery, but GitOps is not the
right mechanism for every source-code edit. The production path is deliberately
slower and more controlled than the development path.

The goal of this document is to keep those loops separate so that application
and AI-assisted development can iterate in seconds without weakening the
production safety model.

## The three loops

```text
fast local loop
    source edit -> local process reload -> targeted test

Kubernetes development loop
    source edit -> local process interception or a warm dev container ->
    real development-cluster dependencies

production promotion loop
    reviewed commit -> CI -> immutable image -> GitOps -> Flux reconciliation
```

Only the third loop is a production deployment. It must remain reviewable,
immutable, and Git-backed.

## Current state

The workspace currently has:

- `cloudnativepong` local mode for the fastest application feedback;
- a persistent public/production-like cluster at context `k3d-pong`;
- GitHub Actions that build and test images on hosted runners;
- Flux polling the application sources and reconciling production manifests;
- no separate persistent `pong-dev` cluster or service-interception workflow yet.

The public `k3d-pong` cluster is **not** a development sandbox. Do not use it
for repeated experiments, temporary image patches, or destructive cluster
lifecycle operations. Until a separate development plane exists, use local mode
for ordinary changes and an explicitly disposable, isolated environment for
Kubernetes integration work.

On the current host, `kubectl` can reach the existing cluster, but the installed
`k3d` command currently cannot list it because it is trying to use Docker while
the cluster is managed through Podman. Fix and verify the Podman/Docker API
configuration before automating any k3d lifecycle operation. Do not work around
that failure by pointing scripts at the public cluster.

## Loop 1: local process development

This is the default loop for Go, game, lobby, database, telemetry, WebSocket,
HTTP, and most frontend changes.

```bash
cd cloudnativepong

# Narrow feedback while editing
go test ./lobby ./db ./telemetry

# Full application unit suite at a checkpoint
go test ./...

# Run the application without Kubernetes
go run . --mode=local

# In another terminal, run one test or the local E2E suite
npx playwright test tests/e2e.spec.ts -g "two players can join"
npx playwright test
```

A file watcher such as Air can restart the local Go process after edits, but it
is optional. The important property is that the process runs locally and is not
rebuilt into a production container for every edit.

Use the narrowest test that answers the current question:

| Change | First feedback |
|---|---|
| game rules | package/unit test |
| lobby or database behavior | affected Go package test |
| HTTP/WebSocket behavior | focused Go test or local Playwright test |
| browser interaction | focused Playwright test |
| broad application change | `go test ./...` and local Playwright |

Before handoff or commit, run the broader checks:

```bash
go test ./...
go test -race ./...
go vet ./...
git diff --check
```

These checks are validation gates, not the default command after every save.

## Loop 2: Kubernetes-dependent development

Some changes genuinely need Kubernetes: Pod and Service orchestration, RBAC,
NetworkPolicies, room callbacks, scheduling, DNS behavior, or the gateway path.
Those changes should use a separate, warm development plane rather than the
production cluster or a newly-created cluster for every edit.

### Preferred target: local process interception

The preferred architecture is:

```text
persistent pong-dev cluster
    gateway, static service, room dependencies, development database

host process
    pong-api running locally with hot reload

interception
    traffic for the development API Service is sent to the host process
```

Tools such as Telepresence or mirrord can provide this class of service
interception. The exact tool is an implementation choice; the invariant is that
changed application code is compiled and restarted locally while it can still
use the development cluster's Kubernetes API and Services.

This avoids the per-edit sequence of:

```text
build image -> push/import image -> change Deployment -> wait for rollout
```

The local process must use only development credentials, namespace, database,
and callback configuration. It must never receive production kubeconfig or
mount the production SQLite PVC.

### Fallback: a warm development container

If interception is not available, use a persistent `pong-dev` cluster with a
development-only image containing the Go toolchain and a file watcher. Sync
source into that container and restart only the affected process.

Development images and production images have different purposes:

```text
 development image: shell, Go toolchain, watcher, source sync
 production image:  minimal distroless image, immutable, signed, promoted by GitOps
```

Do not add a shell or compiler to the production distroless images merely to
make development convenient.

### Dynamic room Pods

Room Pods are a special case because the API creates them from an image.
Develop game logic in local mode first. For Kubernetes-specific room changes:

- rebuild only the room development image;
- recreate only disposable development room Pods;
- keep the API, gateway, and static services unchanged when they are unaffected;
- run the focused two-player Kubernetes test;
- never use the public room namespace as an experiment area.

## Development-plane requirements

A future persistent development environment should have all of these explicit
boundaries:

- context: `k3d-pong-dev`;
- namespace: `pong-dev`;
- separate SQLite database and PVC, if persistence is needed;
- separate local registry and development image names;
- development origins and host ports;
- no production Flux ownership;
- no access to `k3d-pong` resources or production secrets;
- scripts that fail closed unless the selected context is `k3d-pong-dev` or an
  explicitly generated disposable context;
- an easy reset path that cannot delete production resources.

The development cluster should be created once, kept warm, and reused. Cluster
creation belongs to environment setup or CI, not to the normal source-edit
loop.

## Loop 3: production promotion

Production remains GitOps-managed:

```text
reviewed source commit
    -> CI tests
    -> cached immutable image build
    -> SBOM/provenance/attestation checks
    -> production manifest update
    -> Flux reconciliation
    -> rollout and synthetic verification
```

The following are release operations and must not be in the per-edit loop:

- pushing every experiment to GHCR;
- generating deployment commits for every save;
- waiting for Flux polling;
- rebuilding all four images when one component changed;
- running supply-chain scans after every local edit;
- creating a new k3d cluster for every integration test;
- reinstalling Playwright and Chromium for every test invocation;
- testing against the public `k3d-pong` cluster.

Production feedback can still be improved independently with BuildKit layer
caching, parallel or shared image builds, path-based CI selection, cached
Playwright browsers, and a protected Flux webhook receiver. Those optimizations
reduce release latency; they do not replace the local inner loop.

## AI-agent operating rule

An agent should choose the cheapest loop that can answer the question:

1. inspect the changed files;
2. run the narrowest local test;
3. run local mode and a focused browser test if the behavior crosses HTTP or
   WebSocket boundaries;
4. use the isolated Kubernetes development plane only when the change depends
   on Kubernetes behavior;
5. run full validation before handoff;
6. use GitHub Actions and GitOps only for reviewed promotion.

A source edit is not evidence that a production image, production manifest, or
Flux reconciliation should run.

## Target feedback times

These are targets, not guarantees:

| Loop | Target |
|---|---:|
| affected Go test | 1–3 seconds |
| local process restart | 1–3 seconds |
| focused local browser test | 5–15 seconds |
| Kubernetes-aware code edit with interception | 1–10 seconds plus test time |
| warm development-container update | seconds, depending on compilation |
| full release validation | minutes |
| production promotion | minutes, with review and rollout gates |

The key optimization is not making every operation faster. It is avoiding
expensive operations when they are irrelevant to the question being tested.

## References

- [Tilt Live Update](https://docs.tilt.dev/live_update_reference.html)
- [k3d local registries](https://k3d.io/stable/usage/registries/)
- [k3d with Podman](https://k3d.io/v5.9.0/usage/advanced/podman/)
- [Flux webhook receivers](https://fluxcd.io/flux/guides/webhook-receivers/)
- [Docker GitHub Actions cache backend](https://docs.docker.com/build/cache/backends/gha/)
