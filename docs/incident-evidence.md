# Incident evidence and status boundary

This workspace has an explicitly invoked evidence collector at
[`scripts/incident-evidence.sh`](../scripts/incident-evidence.sh). It creates a
local JSON and/or Markdown snapshot; it is not a daemon, monitor, pager, or
cluster controller. The incident response lifecycle, severity levels, roles,
objective postmortem triggers, sanitized incident-state template, and blameless
postmortem template are in [`incident-lifecycle.md`](incident-lifecycle.md).

## Lifecycle at a glance

Declare early when user impact is plausible, name an Incident Commander (IC),
and assign Operations, Communications, and Planning/Follow-up leads. Keep one
UTC timeline, link every observation or hypothesis to a source ID and evidence
timestamp, hand off explicitly, and close only after impact/recovery,
monitoring, communications, action ownership, and the postmortem decision are
recorded. A small incident may combine roles, but the combination and handoff
must be written down.

Automatic postmortem review is required for a critical user-facing failure,
a monitoring blind spot lasting more than two expected hourly observations, any
suspected data-integrity or security event, an approved isolated-drill recovery
objective miss, or a repeat/noisy pattern (two same-signature incidents in 30
days or three human-actionable alerts in seven days). A human may request one
at any time. The public objective is 99% availability per service over 30 days
with no SLA; the separate controlled-drill target is P95 recovery under six
minutes. Neither is established by this collector or by the disposable
capacity-baseline example.

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
page consumes the sanitized v2 artifact from the separate
[`macel94/belacca-status`](https://github.com/macel94/belacca-status) repository.
A GitHub-hosted runner outside the native cluster performs hourly public
checks and commits bounded evidence history. The site keeps an `unknown`
fallback and rejects malformed or expired data. The runner can record an outage
while the cluster is down, but the page itself cannot be served until the
native cluster recovers; this is not multi-region monitoring.
