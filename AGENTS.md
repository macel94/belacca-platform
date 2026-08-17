# Agent instructions: belacca-platform

This repository is the workspace orchestrator, not the application deployment trigger. Read [`docs/gitops-delivery.md`](docs/gitops-delivery.md) before changing or claiming production state.

## Repository routing

- Pong source/images/app overlays: `cloudnativepong/` child repository.
- Portfolio source/site image/site deployment: `francesco-belacca-site/` child.
- Flux/Kubernetes/routing/policy: `belacca-gitops/` child.
- Host/k3s/Ansible prerequisites: `belacca-infrastructure/` child.
- External status artifacts: `belacca-status/` child.
- This parent: submodule gitlinks only.

Always inspect `git -C <child> status`, branch, remote, and `origin/main` before editing. Commit and push the owning child first. Application publish workflows may append a generated deployment commit; fetch it before declaring the child current. Only then update this parent submodule pointer/gitlink when the workspace is intended to track that child revision. A parent commit never publishes an image or deploys an application by itself.

## Production proof

Native production is GitOps-only. After a child publish, verify the immutable image tag/digest, Flux `GitRepository` and Kustomization revisions, workload rollout, health endpoint, build marker, and relevant synthetic journey. Treat Flux `Signature: none` as expected when `spec.verify` is omitted; do not claim Git commit signature verification unless signed commits, a public-key Secret, and live verification are configured.

Do not mutate native production directly with `kubectl apply`, `set image`, or ad hoc registry tags. Use local/disposable targets for development. The full workflow is in `docs/gitops-delivery.md` and the development-loop separation is in `docs/development-loop.md`.
