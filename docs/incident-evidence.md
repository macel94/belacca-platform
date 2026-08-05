# Incident evidence and status boundary

This workspace has an explicitly invoked evidence collector at
[`scripts/incident-evidence.sh`](../scripts/incident-evidence.sh). It creates a
local JSON and/or Markdown snapshot; it is not a daemon, monitor, pager, or
cluster controller.

## Use

From the workspace root, after reviewing the scope:

```bash
./scripts/incident-evidence.sh collect --format both
./scripts/incident-evidence.sh collect --include kubectl,flux --output-dir /tmp/belacca-evidence
```

The tool has a fixed allowlist of `kubectl get`, `flux get`, and read-only Git
status commands. It does not accept arbitrary command arguments, does not run a
shell for collection, never requests Kubernetes Secrets, and never runs
`apply`, `delete`, `patch`, `edit`, `exec`, `run`, `port-forward`, or Flux
reconciliation commands. Each source is bounded by a timeout and combined
output byte limit. Missing binaries, missing kube context, permission errors,
non-zero exits, timeouts, and truncated output are recorded as source failures
so a partial snapshot cannot be mistaken for a healthy one.

The collector is not an automated status publisher. It runs only after a person
explicitly invokes the `collect` subcommand. No credentials, kubeconfig, or
cluster data is committed by the tool.

## Redaction and evidence

Redaction is applied before JSON or Markdown is written. The policy covers
Kubernetes Secret `data`/`stringData` fields, keys and assignments that look
like secrets, tokens, passwords, credentials, cookies, authorization values,
JWTs, private keys, and IPv4/IPv6-like values. The tool also avoids querying
Secrets at all. Redaction is a safety boundary, not proof that arbitrary input
is safe to publish: a human must inspect a bundle before sharing it.

Every source records its request and completion timestamps, command, exit
status, bounded output, redaction counts, and a source reference. Hypotheses
are explicitly labeled, carry a confidence value, and link to source IDs. The
bundle includes empty, pending human-approved-action placeholders; collection
itself approves nothing and performs no action.

## AI-assistance boundary

AI assistance may help summarize or organize this evidence only when it stays
within these boundaries:

1. **Read-only:** inspect the emitted bundle; do not issue cluster mutations,
   use credentials, or turn a diagnosis into an imperative command.
2. **Evidence-linked:** every claim or hypothesis must cite the bundle source
   ID and timestamp; absence of evidence is not evidence of health.
3. **Human approval:** an operator owns interpretation, incident declaration,
   communications, and every action. The placeholders in the bundle are not
   approvals.
4. **GitOps-only changes:** a production change must be proposed, reviewed,
   tested, and applied through the appropriate Git repository and Flux path.
   The evidence collector must never apply a change directly to the cluster.

The public [`francesco.belacca.com/status.html`](https://francesco.belacca.com/status.html)
page consumes only the sanitized `francesco-belacca-site/status.json` contract.
Its checked-in default is `unknown` with uptime `not_configured`. An external,
human-reviewed publisher may replace that static data through the normal
reviewed/GitOps delivery path; there is no cluster-to-browser status API.
