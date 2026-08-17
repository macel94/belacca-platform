# GitOps delivery and commit routing

This workspace contains several independent Git repositories. A change becomes
visible in production only when it is committed and pushed to the repository
that owns the relevant production boundary. The parent
`belacca-platform` repository is an orchestrator and submodule index; pushing
it does not, by itself, publish an application image or deploy a Kubernetes
workload.

## Repository ownership map

| Change | Owning repository | What makes it visible |
|---|---|---|
| Pong source, Dockerfiles, app tests, or Pong application overlays | `cloudnativepong` | Push `main`; GitHub Actions publishes immutable component images, then appends a generated `deploy: publish images ...` commit updating both overlays. Flux watches the child repository. |
| Portfolio source, site assets, Caddy config, or site tests | `francesco-belacca-site` | Push `main`; GitHub Actions publishes the immutable site image, then appends a generated `deploy: publish site ...` commit updating `deploy/kustomization.yaml`. Flux watches the child repository. |
| Kubernetes resources, Flux sources/Kustomizations, routing, policies, or cluster-level app configuration | `belacca-gitops` | Push `main`; the root Flux `GitRepository` and root Kustomization reconcile the native cluster. |
| Host preparation, firewall, k3s, Longhorn prerequisites, or Ansible | `belacca-infrastructure` | Push `main` for source-of-truth visibility, then perform the reviewed Ansible operation in the approved maintenance context. A Git push does not mutate hosts. |
| Hourly external observations, `status.json`, `slo.json`, `badge.json`, and history | `belacca-status` | The scheduled/manual publisher validates and pushes generated artifacts to `main`. This is not a Flux deployment. |
| Workspace submodule revisions and cross-project review pointers | `belacca-platform` | Update the child checkout to the desired remote commit, commit the gitlink, and push the parent. This records a workspace view; it does not replace the child publish or Flux steps. |

The public production plane is the native `belacca-native` cluster. Do not use
it as a development sandbox and do not use `kubectl apply`, `kubectl set
image`, or an ad hoc registry tag as a permanent production change.

## The production promotion chain

For an application change, the normal chain is:

```text
source edit
  -> commit and push application main
  -> application CI tests
  -> immutable GHCR image tagged sha-<source-commit>
  -> SBOM/provenance/attestation/security gates
  -> generated deployment commit updates an immutable image digest
  -> child Flux GitRepository fetches the generated commit
  -> child Flux Kustomization applies the application path
  -> Deployment rolls out the image
  -> health, build marker, and external journey are verified
```

There are two commits by design:

1. **Source commit**: the human-reviewed application change. Its full SHA is
   embedded in the image/build marker and image tag.
2. **Generated deployment commit**: created by the successful publish workflow.
   It changes only the immutable image tag/digest in the application deployment
   Kustomization. Flux normally reports this later commit as the source and
   applied revision, while the running image tag still identifies the source
   commit.

Therefore, these values are expected to differ:

```text
Flux GitRepository revision       = generated deployment commit
Flux Kustomization revision       = generated deployment commit
Deployment image tag              = sha-<source commit>
Deployment image digest           = digest produced by CI for that image
Visible application build marker  = short source commit
```

Do not mistake the generated deployment commit for a second application
release, and do not stop at a successful image publish. The rollout and live
marker must be checked.

## Exact application workflow

When changing `cloudnativepong` or `francesco-belacca-site`:

1. Identify the child repository from the changed path. Do not edit a nested
   checkout as if it were part of the parent repository.
2. Inspect its branch, remote, status, current source commit, and deployment
   workflow. Work on the configured `main` branch unless the task explicitly
   requires a review branch.
3. Run the narrowest useful local tests, then the repository's full required
   test suite before handoff.
4. Commit the source change in the child repository and push `main`.
5. Watch the child repository's publish workflow. A successful test job is not
   enough; wait for the image publish, attestations/security gates, and the
   generated deployment commit.
6. Fetch the child remote again. Treat the generated deployment commit as the
   latest child `origin/main` when checking what Flux will consume.
7. Reconcile and inspect the matching Flux resources:

   ```bash
   flux reconcile source git cloudnativepong -n flux-system
   flux reconcile kustomization pong -n flux-system

   flux reconcile source git francesco-belacca-site -n flux-system
   flux reconcile kustomization portfolio -n flux-system
   ```

   Use only the resource pair relevant to the change. The installed CLI may
   not support `--with-source` on every reconcile subcommand; separate source
   and Kustomization commands are the portable form.
8. Verify all layers, not just `Ready=True`:

   ```bash
   flux get sources git -A
   flux get kustomizations -A
   kubectl -n pong get deploy,pods -o wide                 # Pong
   kubectl -n portfolio get deploy,pods -o wide            # portfolio
   kubectl -n <namespace> get deployment <name> -o yaml    # image/digest
   curl -fsS https://pong.belacca.com/                    # Pong
   curl -fsS https://francesco.belacca.com/               # portfolio
   ```

   Also verify the application-specific build marker, health endpoint, and
   external synthetic journey where available.
9. Update the parent submodule pointer only after the child remote contains the
   generated deployment commit:

   ```bash
   git -C <child> fetch origin main
   git -C <child> checkout main
   git -C <child> merge --ff-only origin/main
   git add <child>
   git commit -m "chore: pin latest <child> deployment"
   git push origin main
   ```

   The parent pointer is bookkeeping for this workspace. It must never be
   treated as the application publish trigger.

### Site-specific path

- Child source: `macel94/francesco-belacca-site`
- Flux source: `flux-system/francesco-belacca-site`
- Flux Kustomization: `flux-system/portfolio`
- Flux path: `./deploy`
- Publish workflow: `.github/workflows/test-and-publish.yml`
- Generated file: `deploy/kustomization.yaml`
- Runtime namespace/deployment: `portfolio/francesco-site`
- Runtime image: `ghcr.io/macel94/francesco-belacca-site`
- Runtime proof: `GET /health`, homepage build marker, favicon/assets, and
  external portfolio checks

The site workflow's generated deployment commit is expected to follow the
source commit. The image tag/digest in that generated commit is the release
that must be present in the live Deployment.

### Pong-specific path

- Child source: `macel94/cloudnativepong`
- Flux source: `flux-system/cloudnativepong`
- Flux Kustomization: `flux-system/pong`
- Flux path: `./k8s/overlays/native-staging` (native production)
- Compatibility path: `./k8s/overlays/server`
- Publish workflow: `.github/workflows/publish-images.yml`
- Generated files: both native-staging and server image overlays
- Runtime namespace: `pong`
- Runtime proof: health/readiness, image tags/digests for all affected
  components, rollout state, and the external two-player journey

Never use the historical `k3d-pong` target or the public native namespace for
routine iteration. Use local mode or a disposable isolated Kubernetes target.

## GitOps repository workflow

For a change owned by `belacca-gitops`:

1. Edit the cluster resource, source, Kustomization, routing, policy, or
   documentation in `belacca-gitops`.
2. Render and validate the affected Kustomizations locally and run the GitOps
   repository tests.
3. Commit and push `belacca-gitops/main`.
4. Reconcile the Flux root or affected child after the remote commit is
   available:

   ```bash
   flux reconcile source git flux-system -n flux-system
   flux reconcile kustomization flux-system -n flux-system
   flux get sources git -A
   flux get kustomizations -A
   ```

5. Verify the applied GitOps revision, resource health, rollout, and public
   behavior. A successful GitOps commit or Flux source fetch alone is not proof
   of an application rollout.

Application image pins normally belong in the application repository's
workflow-generated deployment Kustomization. Do not manually edit a child
application's generated image pin from `belacca-gitops` unless the documented
release/rollback procedure explicitly assigns that ownership.

## Status repository workflow

`belacca-status` is an external evidence publisher, not a Flux child. For
collector or policy code changes:

1. Commit and push the source change to `belacca-status/main`.
2. Run the local tests and validators.
3. Dispatch or wait for `.github/workflows/publish-status.yml`.
4. The workflow validates and commits `status.json`, `history/`, `slo.json`,
   and `badge.json` itself. Do not assume the source commit is the latest
   published observation commit.
5. Verify the generated artifact commit and public status/reliability surfaces.

A status artifact describes external observations; it does not change a
Kubernetes Deployment and must not be used as production rollout evidence.

## Infrastructure repository workflow

`belacca-infrastructure` owns host preparation and prerequisites, not
Kubernetes application manifests. For an infrastructure change:

1. Edit the Ansible inventory, policy, playbook, or host documentation.
2. Run syntax, policy, check-mode, and repository tests.
3. Commit and push `belacca-infrastructure/main`.
4. Obtain the required human approval/maintenance window.
5. Run the reviewed playbook against the explicitly selected native hosts and
   verify host and cluster recovery read-only afterward.

Never put kubeconfigs, join tokens, SOPS age private keys, OAuth credentials, or
provider secrets in the repository. Do not claim a host change is live because
its Git commit exists.

## Signatures and verification status

A Flux `GitRepository` with `spec.verify` omitted has no Git commit signature
verification configured. A UI value such as `Signature: none` is therefore
normal for the current child sources and means **unsigned Git commit
verification is not enabled**; it does not mean that the source artifact failed
or that the Flux source is stale.

This is separate from container supply-chain verification. Application publish
workflows produce GHCR image digests, SBOMs, provenance, and vulnerability
attestations; Kyverno verifies those image attestations at admission. Flux
source commit verification would require a separate reviewed setup with signed
commits and a public-key Secret. Do not add a `verify` block or claim signed
GitOps commits unless that setup has actually been provisioned and observed.

## Parent workspace synchronization

The parent repository records submodule gitlinks for local review. After a
child's generated deployment commit lands, synchronize and commit the parent
pointer if the workspace is intended to reflect the latest child:

```bash
make update
# review every gitlink; do not blindly accept unrelated movement
git diff --submodule=log
git add <intended-child>
git commit -m "chore: pin latest <child> deployment"
git push origin main
```

If only a child repository was requested, the child push is the deployment
operation; a parent pointer update is a separate bookkeeping commit. Never
report the parent commit as the deployed application revision without checking
Flux and the workload image.

## Completion checklist

A change is complete only when the applicable items are true:

- [ ] The owning repository is identified and its local tests pass.
- [ ] The source commit is pushed to the correct `main` branch.
- [ ] Any generated publish/deployment commit has landed and is fetched.
- [ ] The immutable image tag and digest are present in the owning deployment
      Kustomization.
- [ ] Flux source and child Kustomization report the expected revision and
      `Ready=True`.
- [ ] The workload image/digest and rollout are verified in Kubernetes.
- [ ] The public health/build marker/synthetic journey is verified where
      applicable.
- [ ] The parent gitlink is updated only when workspace synchronization is
      intended.
- [ ] No direct production mutation, plaintext secret, or unsigned-commit
      verification claim was introduced.
