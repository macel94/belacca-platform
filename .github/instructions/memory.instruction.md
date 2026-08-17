---
applyTo: '**'
---

# Persistent user preference: GitOps-aware delivery

For the `belacca-platform` workspace and its child repositories, automatically
route every change through the repository that owns the changed boundary. Do
not wait for the user to identify the repository or deployment path.

## Repository routing

- `cloudnativepong`: Pong source, images, tests, and application overlays.
- `francesco-belacca-site`: portfolio source, site image, tests, and `deploy/`.
- `belacca-gitops`: Flux sources/Kustomizations, Kubernetes resources, routing,
  policies, and cluster-level configuration.
- `belacca-infrastructure`: Ansible, host preparation, firewall, k3s, and
  storage prerequisites.
- `belacca-status`: external status/SLO/badge/history publication.
- `belacca-platform`: workspace orchestration and submodule gitlinks only.

## Required application release behavior

For Pong or the portfolio, commit and push the source change in the child
repository first. Wait for its GitHub Actions publish workflow to pass and for
the generated deployment commit to land. Fetch that generated commit before
considering `origin/main` current. It contains the immutable image tag/digest
that Flux will consume. Then reconcile and verify the matching Flux
`GitRepository`, child Kustomization, workload image/digest, rollout, health,
build marker, and relevant public synthetic journey.

Expected revision distinction:

- Flux source/Kustomization revision: generated deployment commit.
- Running image tag/build marker: original source commit.
- Running image digest: immutable digest produced by CI.

Only after the child remote has converged to the generated deployment commit,
and only when the workspace should track it, update the parent submodule
pointer and push the parent. A parent push alone never publishes or deploys an
application.

For `belacca-gitops`, push reviewed manifest changes to `main`, reconcile Flux,
and verify applied revisions and runtime state. For `belacca-infrastructure`, a
push records the Ansible/host source but a separately approved maintenance
operation is required to mutate hosts. For `belacca-status`, the publisher
workflow creates generated observation commits; fetch and verify those before
claiming public evidence is current.

Native production is GitOps-only. Never use direct `kubectl apply`, `kubectl set
image`, mutable `latest` tags, or native production as a development sandbox.

`Signature: none` on a Flux GitRepository is expected when `spec.verify` is
omitted; it means Git commit signature verification is not configured. Do not
claim signed GitOps commits or add verification until signed commits, a public
key Secret, and live Flux verification have been deliberately provisioned.

Canonical operating guide:
https://github.com/macel94/belacca-platform/blob/main/docs/gitops-delivery.md
