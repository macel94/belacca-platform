# Controlled-drill recovery objective

## Objective and boundary

The platform has two separate internal reliability objectives:

| Objective | Definition | Evidence | Boundary |
|---|---|---|---|
| **Availability SLO** | 99% per supported public application over a rolling 30-day window | Durable, sanitized external observations in `belacca-status` | Not an SLA; controlled drills are not counted as availability success/failure arithmetic |
| **Controlled-drill recovery objective** | P95 recovery **strictly under 360 seconds** across repeated comparable drills | This document's sanitized drill records | Internal RTO target for approved controlled drills; not an SLA and not a promise for every real incident |

The recovery objective applies only to a declared, controlled fault in one of the
following scopes:

- native-production edge, control-plane, or application drills;
- isolated capacity or chaos environments.

A disposable capacity baseline, one observation snapshot, an availability
window, or an unapproved experiment cannot establish this objective. Recovery
failures do not change the target: they require a follow-up issue or
postmortem.

The objective follows a steady-state experiment model: define observable
recovery checks, introduce one bounded fault, and compare the observed recovery
against the target. The record is evidence only. This repository provides no
fault injector, cluster mutator, credential handling, public-probe runner, or
automatic approval path.

## Definitions

- **Start:** the timestamp of controlled fault injection, or the timestamp of a
  confirmed actionable failure alert for a non-injection drill.
- **Stop:** the timestamp after health, API CRUD, the canonical Pong two-player
  journey where applicable, and cleanup all pass. For a non-Pong service, the
  Pong journey must be recorded as `not_applicable` with a reason; it cannot be
  silently omitted.
- **Duration:** `stop.timestamp - start.timestamp`, in seconds. Record UTC `Z`
  timestamps and validate the duration rather than calculating it by hand.
- **Target:** P95 recovery duration **strictly less than 360 seconds**. A P95 of
  exactly 360 seconds fails the target.
- **P95 method:** nearest-rank: sort comparable durations, then select the item
  at one-indexed rank `ceil(0.95 * n)`. This method is deterministic for the
  small sample sizes used here.
- **Comparable:** repetitions share the same fault class, environment scope,
  recovery-check contract, and runbook revision. Do not combine unrelated
  faults, topology changes, or materially different mitigations into one P95.
- **Minimum evidence:** at least three comparable repetitions before any P95
  result may be claimed.

## Approval and safety gates

Every drill must be approved before execution by an accountable operator. The
approval reference, approver role, bounded fault scope, abort conditions, and
rollback/cleanup plan belong in the evidence record. Approval is not created by
this repository or by its validator.

### Default-deny rules

1. **Do not target the live public endpoint by default.** Start in an isolated
   capacity/chaos environment with a private or loopback-only target reference.
   The evidence validator rejects public hostnames and URLs.
2. **Do not use native production as a development sandbox.** A native
   production drill requires a separately approved change reference and a
   human-operated, reviewed GitOps or infrastructure procedure. It must not be
   run by this repository's scripts.
3. **One fault at a time.** Do not combine node loss, routing changes, storage
   operations, image changes, and load generation in one repetition.
4. **Bound blast radius.** Define the exact workload, namespace, environment,
   duration, abort conditions, observer, and cleanup owner before approval.
5. **Protect state.** Never delete or overwrite production PVCs, SQLite data,
   Secrets, credentials, player data, or public DNS records as a drill.
6. **Stop on uncertainty.** Abort when the target is ambiguous, the selected
   context cannot be proven isolated, an abort condition occurs, or monitoring
   cannot distinguish experiment traffic from user traffic.
7. **Do not spend the availability error budget on experiments.** A drill must
   be excluded from the public availability arithmetic and any impact must be
   recorded separately.
8. **No silent target changes.** A missed target remains a miss. Open a
   follow-up issue/postmortem with an owner and validation criterion.

The validator is read-only and fail-closed; it does not check a kube context,
approve an action, inject a fault, run recovery checks, call an endpoint, or
clean up an environment.

## Approved execution sequence

This sequence is a human-operated checklist, not an executable command list.
Use the isolated environment's own reviewed runbook for fault injection and
cleanup.

### Before the drill

- [ ] Record the drill ID, environment reference, scope, fault class, and
      comparability key.
- [ ] Confirm the target is isolated or obtain the separately recorded
      production approval; never use a live public endpoint as the default.
- [ ] Confirm the selected context/target cannot reach production namespaces,
      PVCs, Secrets, credentials, or public DNS.
- [ ] Record approval, change reference, observer, abort conditions, and the
      cleanup/rollback owner.
- [ ] Establish steady state with the exact recovery checks below and record
      sanitized evidence references.
- [ ] Confirm a post-drill observation window and a path to open a follow-up
      issue/postmortem.

### During the drill

- [ ] Record **start** immediately at fault injection, or at the confirmed
      actionable alert for a non-injection drill.
- [ ] Apply only the approved, bounded fault through the environment's reviewed
      mechanism. Do not improvise a broader mutation.
- [ ] Preserve timestamps from an evidence source; do not use a later narrative
      estimate.
- [ ] Abort and preserve the evidence if an abort condition or unexpected user
      impact occurs.

### Stop and recovery checks

Record each check's exact action, result, observation timestamp, and sanitized
evidence reference. The stop timestamp is after the final required check passes.

| Check ID | Required exact check (adapt only to the approved isolated target) |
|---|---|
| `health` | Health/readiness endpoint returns the documented success response and the workload/control-plane health observation is passing. Record the exact path or API operation, expected status, and evidence source; do not record response bodies containing private data. |
| `api-crud` | API list/read, create, update/join where supported, and delete/cleanup operations all return their documented success results. Use synthetic data only; record operation names/statuses, never IDs, player names, tokens, or response bodies. |
| `canonical-pong-two-player-journey` | Where Pong applies: homepage, API room creation, two unique synthetic players join, playing state/WebSocket-compatible journey, and normal end-of-game path pass. Record the check definition and pass evidence, not room IDs or player data. For other services: `not_applicable` plus the service/scope reason. |
| `cleanup` | The synthetic resources and fault are fully removed/reverted, no orphan workload/resource remains in the approved scope, and the post-drill observation is healthy. Record the cleanup verification reference. |

Set **stop** only after all four records are `pass` or the Pong check is
explicitly `not_applicable` for a non-Pong scope. A failed check means the
repetition failed; it does not permit moving stop earlier.

### After the drill

- [ ] Verify the exact target and environment are back within steady state.
- [ ] Record impact as sanitized user impact or `none observed`; do not claim
      no impact merely because a local check passed.
- [ ] Run `make drill-validate RECORD=path/to/record.json`.
- [ ] Add comparable records only when the fault class, scope, checks, and
      runbook revision remain comparable.
- [ ] Do not claim P95 until three or more comparable repetitions validate.
- [ ] If any repetition fails, lasts at least 360 seconds, or the batch P95 is
      not strictly under 360 seconds, open a follow-up issue/postmortem. Keep
      `target_status: fail`; do not edit the objective.

## Evidence record

The machine-readable contract is
[`controlled-drill-recovery.schema.json`](controlled-drill-recovery.schema.json).
Validate a sanitized record without executing a drill:

```bash
make drill-validate RECORD=/path/to/controlled-drill-record.json
```

Use one batch record for comparable repetitions. The required shape is shown
below; replace placeholders and preserve the exact check IDs. This is a
structure example, not evidence of an executed drill and must not be copied as
an unreviewed result.

```json
{
  "$schema": "https://raw.githubusercontent.com/macel94/belacca-platform/main/docs/controlled-drill-recovery.schema.json",
  "schema_version": "belacca.controlled-drill-evidence.v1",
  "sanitized": true,
  "record_type": "controlled_drill_batch",
  "objective": {
    "id": "belacca-controlled-drill-recovery-v1",
    "availability_slo": {
      "target_percent": "99%",
      "window": "rolling_30d",
      "sla": false,
      "separate_from_recovery_objective": true
    },
    "recovery_target_seconds": 360,
    "percentile": "P95",
    "comparison": "strictly_under",
    "minimum_comparable_repetitions": 3
  },
  "environment": {
    "scope": "isolated-capacity-chaos",
    "environment_reference": "<isolated-environment-reference>",
    "production": false
  },
  "safety": {
    "approved": true,
    "approval": {
      "approver_role": "<accountable-operator-role>",
      "approved_at": "<UTC timestamp ending in Z>",
      "change_reference": "<ticket-or-change-reference>"
    },
    "bounded": {
      "fault_scope": "<one fault and exact isolated target>",
      "abort_conditions": ["<observable abort condition>"],
      "rollback_or_cleanup_plan": "<reviewed cleanup reference>"
    },
    "public_endpoint_targeted": false,
    "target_reference": "<private isolated target reference>",
    "mutation_performed": true
  },
  "repetitions": [],
  "evaluation": {
    "comparable_repetition_count": 0,
    "p95_method": "nearest_rank",
    "p95_duration_seconds": null,
    "target_status": "not_claimed",
    "claimable": false
  },
  "limitations": [
    "No repetition is recorded in this template; it is not evidence of recovery performance."
  ]
}
```

The template intentionally has no repetitions and cannot pass validation. A
real record must contain timestamps, exact checks, and evidence references for
every repetition. Never record secrets, tokens, credentials, player data, room
IDs, client addresses, raw private logs, or unredacted response bodies.

## Reporting and follow-up

The batch is **claimable** only when at least three comparable repetitions are
present and valid. The validator calculates nearest-rank P95 and requires the
recorded result to agree with it. P95 `< 360` seconds is a pass; P95 `>= 360`
seconds is a fail.

A failed recovery check, individual duration at/over 360 seconds, invalid or
incomplete evidence, or failed batch P95 requires a follow-up issue or
postmortem. The follow-up must identify the sanitized failure mode, owner,
proposed improvement, and validation criterion. It must not silently loosen the
fault, change comparability, remove a check, or change the target.

A record that cannot be validated is **not** a failed recovery measurement by
itself; it is incomplete evidence and must not be used to claim performance.

## Current validation limitation and operator follow-up

This clean worktree has no production credentials, cluster access, approved
change window, isolated chaos environment, or executed drill evidence. No
production experiment was performed and no P95 performance claim is made here.
Before claiming the objective, an operator must provision or select a separate
isolated environment, obtain documented approval, execute at least three
comparable repetitions using the environment-specific reviewed fault and
cleanup procedure, sanitize the evidence, validate the batch, and open a
follow-up issue/postmortem for every miss.

## References

- [Issue #4](https://github.com/macel94/belacca-platform/issues/4)
- [Google SRE: Implementing SLOs](https://sre.google/workbook/implementing-slos/)
- [Google SRE: Incident response](https://sre.google/workbook/incident-response/)
- [Principles of Chaos Engineering](https://principlesofchaos.org/)
- [Incident lifecycle](incident-lifecycle.md)
- [Incident evidence boundary](incident-evidence.md)
- [Native production reliability metadata](../belacca-gitops/docs/RELIABILITY.md)
