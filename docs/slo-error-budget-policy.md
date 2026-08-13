# Initial internal SLO and error-budget policy

**Policy ID:** `belacca-slo-99-v1`
**Owner:** platform
**Status:** approved initial engineering policy
**Review:** monthly, and after a material incident, target change, measurement-source change, or capability change

This policy connects a user-facing service-level indicator (SLI) to an SLO,
error budget, and engineering release/reliability decision. It follows the
Google SRE model; it is an internal decision tool, not a customer-facing
promise.

The normative machine-readable contract is
[`slo-policy.json`](slo-policy.json), validated by
[`scripts/validate_slo_policy.py`](../scripts/validate_slo_policy.py).

## Scope and target

Each supported public application has one initial availability objective:

- **Portfolio:** 99% over a rolling 30-day window.
- **Pong:** 99% over a rolling 30-day window.
- **Analytics:** 99% over a rolling 30-day window.

The 30-day hourly window has 720 expected slots. At 99%, the theoretical
error budget is 1% of the window, or **7.2 bad hourly slots**. This sampled
slot budget is not a claim that 7.2 hours of continuous outage can be safely
ignored: a low-rate probe can miss short or partial failures, and incident
response remains independent of budget arithmetic.

This is an **internal engineering objective**. It is **not an SLA, warranty,
customer promise, service-credit commitment, or compensation obligation**. No
service may claim 99% until a complete valid measurement window exists.

Protected operator surfaces (Headlamp/dashboard, Flux Web UI, and the Dex alias)
have a separate conditional 99%/30-day objective in the policy contract, but it
is disabled and not configured today. It becomes eligible only after an
approved authenticated measurement path exists. The current catalog and
synthetic contract intentionally keep it `not_configured`; redirects or
unauthenticated checks do not qualify.

## SLI and observation contract

The durable source is the sanitized, external hourly history and `slo.json`
artifact published by [`macel94/belacca-status`](https://github.com/macel94/belacca-status).
Native Prometheus metrics in
[`macel94/belacca-gitops`](https://github.com/macel94/belacca-gitops) are private
diagnostics and are not the public availability SLI.

| Service | User journey | Numerator (good slot) | Denominator |
|---|---|---|---|
| Portfolio | External canonical `/health` and homepage request | A slot where both critical checks pass | All 720 expected hourly slots |
| Pong | Homepage, health, room create/join, two-player WebSocket-compatible playing state, and cleanup | A slot where every critical stage passes | All 720 expected hourly slots |
| Analytics | Public `/status` and fixed harmless same-origin `/count` probe | A slot where both checks pass | All 720 expected hourly slots |

The source may retry a check up to three times. A valid failed journey after
those attempts is **bad**, not unknown. `/count.js` and portfolio aliases are
supporting diagnostics; they do not create additional services or denominators.
Native WebTransport is optional and does not silently replace Pong’s measured
WebSocket-compatible journey.

### Good, bad, and unknown observations

- **Good:** a valid hourly observation proves every critical stage of the
  service’s defined journey passed under the source retry policy.
- **Bad:** a valid hourly observation exists and at least one critical stage
  failed after retries. It consumes one bad slot.
- **Unknown:** the slot is absent, malformed, stale, ambiguously duplicated,
  missing a required component, or otherwise cannot be classified from
  sanitized evidence. Unknown never counts as good or bad.

The denominator remains all 720 expected slots. Missing monitoring data is not
implicitly healthy and does not refill the budget. Any unknown, invalid, or
incomplete slot prevents a numeric SLO/error-budget claim and puts the service
in **caution/review** until the evidence source is repaired. A short probe,
status-page response, native metric, incident bundle, or partial history cannot
prove 99%.

## Error-budget decision policy

Evaluate each service independently from the complete valid rolling window.
Unknown data takes precedence over release confidence. An active user-impacting
incident takes precedence over arithmetic.

| State | Entry condition | Engineering action |
|---|---|---|
| **Normal delivery** | Complete valid window; no active user-impacting or measurement incident; fewer than 3.6 bad slots (under 50% of budget) | Normal reviewed delivery is allowed. Keep ordinary testing, rollback readiness, and evidence review. |
| **Caution/review** | 3.6–under 7.2 bad slots, **or any incomplete/unknown/stale measurement window** without an active user-impacting incident | Owner and reviewer assess reliability risk before non-trivial delivery. Prefer small, reversible, observable changes and repair evidence gaps. |
| **Reliability-first** | 7.2 or more bad slots, an active user-impacting incident, or evidence failure prevents safe decisions during an active incident | Pause non-emergency feature delivery. Prioritize mitigation, rollback/recovery, monitoring repair, and written review. Urgent reliability work may proceed only with human approval. |

This policy never authorizes direct production mutation. Production changes are
reviewed and applied through the owning repository and Flux/GitOps path. Return
to normal delivery only after recovery, evidence validity, and the next review
are recorded; there is no administrative budget reset.

## Three distinct signals

These signals must not be conflated:

1. **Public status** (`status.json` and the website): a fresh, sanitized
   communication artifact with operational/degraded/incident/unknown state. It
   is not an SLO calculation, durable availability proof, or pager.
2. **SLO evidence** (`history/` and `slo.json`): durable sanitized evidence for
   internal engineering review. Numeric values are withheld until the complete
   720-slot window is valid. It is not a public uptime claim.
3. **Paging:** an actionable alert path with an owner, tested delivery, and
   separately reviewed thresholds (for example, burn-rate policy). Status
   publication and native diagnostics do not constitute paging. No paging
   capability is claimed until it is validated.

Evidence stays sanitized: never store credentials, tokens, cookies, room IDs,
player names, addresses, response bodies, or unredacted private telemetry.

## Owners, sources, and review cadence

Platform owns the policy and the catalog metadata. The status repository owns
durable external observation and SLO evidence. GitOps owns native production
routing, workload paths, and private diagnostic implementation. Pong owns its
application journey and aggregate diagnostics. The service catalog records each
owner, measurement source, runbook, and live native implementation path at
[`belacca-gitops/catalog/services.json`](https://github.com/macel94/belacca-gitops/blob/main/catalog/services.json).

Review this policy monthly and whenever any of the following changes:

- a public journey, hostname, route, release path, or native implementation;
- the external observation schema, cadence, retry, retention, or privacy
  boundary;
- an error-budget threshold, target, window, or unknown-data rule;
- a material incident, evidence gap, or proposed paging path; or
- the protected operator authentication path becomes safe and measurable.

## Cross-repository implementation work

- [`belacca-status#1`](https://github.com/macel94/belacca-status/issues/1) —
  durable 99% SLO and error-budget evidence.
- [`belacca-gitops#2`](https://github.com/macel94/belacca-gitops/issues/2) —
  native service observability and SLO recording/alerting implementation;
  native metrics remain diagnostics until this policy’s external source is
  complete.
- [`cloudnativepong#17`](https://github.com/macel94/cloudnativepong/issues/17)
  — align Pong telemetry and synthetic journey with this SLO.

The controlled-drill recovery objective (P95 under six minutes) is a separate
policy and is excluded from availability arithmetic.
