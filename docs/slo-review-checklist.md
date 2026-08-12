# SLO and live-capability review checklist

Use this checklist for a target change, a new/changed supported service, or a
claim that a capability is live. A checked box records that the change was
reviewed; it does not itself prove runtime health or authorize production
mutation.

## Change or target review

- [ ] The change names the service and user journey, and confirms whether it is
      public or a protected operator surface.
- [ ] The target, window, observation cadence, numerator, denominator, and
      7.2-slot 1% budget are explicit and consistent with
      [`slo-policy.json`](slo-policy.json).
- [ ] Good, bad, and unknown observations are defined. Missing, malformed,
      stale, ambiguous, or incomplete data never counts as good.
- [ ] The complete 720-slot rule is retained: no claim from a snapshot or
      incomplete window, and no administrative budget reset.
- [ ] The measurement source, retry/aggregation behavior, evidence retention,
      privacy boundary, and source owner are named.
- [ ] The review identifies whether the change affects `status.json`, durable
      `slo.json` evidence, paging, or more than one. Those signals remain
      separate.
- [ ] The error-budget action thresholds are preserved: normal delivery below
      50%, caution/review from 50% or unknown data, reliability-first at
      exhaustion or active user impact.
- [ ] The wording remains internal and non-SLA: no customer promise, credit,
      compensation, or contractual uptime language.
- [ ] The relevant service catalog entry, runbook, implementation path, and
      review cadence are updated together.
- [ ] The dependent repository issue(s) are cross-linked and the owning
      repository’s tests/validators are identified.
- [ ] `python3 scripts/validate_slo_policy.py`, relevant child validators, and
      deterministic tests pass. Rendered manifests are reviewed when routing or
      native implementation paths change.

## Declare a capability live

Do not mark a capability live based only on committed metadata, a successful
render, a single probe, or a status-page response. All applicable items below
must be evidenced by an operator without placing secrets or private telemetry
in Git.

- [ ] The live native-production implementation path is identified in
      `belacca-gitops` and matches the catalog and routing inventory.
- [ ] The owner has confirmed the intended public journey and its dependency
      boundaries in the deployed native path.
- [ ] The measurement source is running on its intended schedule from its
      intended failure domain, and durable sanitized history is being retained.
- [ ] A complete valid 720-slot window exists before any numeric 99% claim is
      made; otherwise the state remains proposed/insufficient-data/unknown.
- [ ] A valid failed journey is recorded as bad, while missing or malformed
      evidence is recorded as unknown and blocks claims.
- [ ] Status publication, SLO evidence, and paging have been tested as separate
      paths. No status artifact is treated as a page.
- [ ] Alert ownership, burn-rate thresholds, routing, delivery, suppression,
      and human escalation have been tested if paging is claimed.
- [ ] Privacy review confirms that no credentials, tokens, cookies, room IDs,
      player names, addresses, response bodies, or unredacted private telemetry
      are collected.
- [ ] Recovery/rollback and the relevant runbook have been exercised in an
      approved environment; a disposable baseline is not production evidence.
- [ ] A human records the evidence references, timestamps, limitations, and
      approval decision. Production changes remain reviewed GitOps/Flux work.

## Protected operator-surface activation

The operator objective stays `not_configured` unless every item below is true:

- [ ] An operator-managed identity and approved authenticated external probe
      exist outside the public status artifact.
- [ ] Secret handling, rotation, access scope, and non-storage of credentials,
      tokens, and cookies are reviewed.
- [ ] The probe verifies an authenticated user journey rather than a redirect,
      login page, or unauthenticated HTTP success.
- [ ] Owner, source, cadence, unknown policy, alert route, runbook, and catalog
      metadata are complete.
- [ ] Runtime validation is complete and the exact evidence is retained in a
      safe operator-controlled location.
- [ ] The policy contract, synthetic contract, and catalog are updated in one
      reviewed change before activation.
