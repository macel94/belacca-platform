# Blameless postmortem — GAME-DAY-NATIVE-20260810 — fail-closed native failure-drill rehearsal

- **Incident state record:** `GAME-DAY-NATIVE-20260810` (controlled game-day record)
- **Severity and trigger(s):** SEV-4 exercise; no production incident and no postmortem trigger from user impact
- **Exercise window (UTC):** 2026-08-10 15:46:09.062Z — 15:50:56.958Z
- **Review status:** closed after sanitized review
- **Review date/participants:** 2026-08-10 UTC; Incident Command, Operations, Communications, and Planning/Follow-up roles

## Classification and safety boundary

This is a completed **fail-closed game-day/tabletop rehearsal**, not a completed
runtime failure/recovery drill. The approved native failure-drill tool executed
its read-only plan for three scenarios and correctly stopped before cordon,
drain, reboot, or uncordon. No production mutation was attempted. The exercise
therefore validates detection of unsafe preconditions and preservation of the
abort boundary; it does not measure recovery time, public user impact, the 99%
availability objective, or the P95-under-six-minute drill objective.

This document contains only sanitized references and observations. It contains
no secrets, player data, tokens, credentials, addresses/private identifiers, or
unredacted private telemetry. Raw report output is not copied here.

## Impact

- **User/service impact:** none observed or caused; the native production
  cluster remained unchanged. The final read-only edge snapshot returned HTTP
  200 for the documented portfolio, Pong, and analytics probes, but that
  snapshot is not an SLO measurement.
- **Detection-to-declaration:** immediate exercise declaration at the first
  plan; this was a scheduled game-day, not an incident declaration.
- **Business/data/security impact:** none evidenced. No application state,
  player data, PVC, DNS, firewall, Longhorn setting, or GitOps resource was
  changed.

## Detection and response

- **How detected:** the fail-closed preflight identified an SSH identity
  mismatch for `control-plane-01` and zero allowed disruptions in the target
  Longhorn InstanceManager PDB for both edge scenarios.
- **What was not detected:** no runtime failure was injected, so recovery,
  external user impact, and drill-time synthetic behavior were not measured.
- **Response roles and handoffs:** the exercise used the IC, OL, CL, and PFL
  roles. The IC retained the single-writer record; OL interpreted plan results;
  CL kept the result classified as no-impact and non-public; PFL maintained
  evidence references and follow-up disposition.

## Timeline (UTC)

| Time | Observation, decision, action, or communication | Evidence refs |
|---|---|---|
| 2026-08-10T15:46:09.062Z | Plan for `control-plane-01` passed cluster preflight but stopped on the checked-in SSH identity mismatch. No mutation was attempted. | `DRILL-CONTROL-20260810T154609.062Z` |
| 2026-08-10T15:50:26.177Z | Plan for `edge-storage-03` passed read-only health gates but stopped because the target Longhorn InstanceManager PDB allowed zero disruptions. No bypass was approved. | `DRILL-EDGE03-20260810T155026.177Z` |
| 2026-08-10T15:50:56.958Z | Plan for `edge-storage-02` stopped on the same zero-disruption PDB condition. The IC closed the exercise as a successful fail-closed rehearsal, not as recovered service. | `DRILL-EDGE02-20260810T155056.958Z` |
| 2026-08-10T15:50:56.958Z | Communications classification recorded: no production impact, no runtime recovery result, and no SLO claim. | `DRILL-EDGE02-20260810T155056.958Z` |

## Contributing factors and hypotheses

- **Contributing factors:** the host identity inventory was inconsistent for
  one target, and Longhorn protection correctly prevented an unsafe disruption
  for the two edge targets. The runbook intentionally treats both conditions
  as stop conditions.
- **Confirmed cause:** not applicable; no service failure occurred.
- **Rejected/remaining hypotheses:** the rehearsal provides no evidence about
  application recovery under node loss. Runtime recovery remains unmeasured
  until a complete plan is approved and a one-node scenario executes.
- **Blameless check:** the system and safety gates behaved as designed. The
  blockers are operational prerequisites to resolve through the owning review
  paths, not individual or team fault.

## What went well / poorly

- **Went well:** bounded preflight ran before mutation; the tool rejected the
  identity mismatch; PDB protection was honored; no force eviction, reboot,
  direct cluster mutation, or GitOps bypass occurred; sanitized reports were
  generated and inspected.
- **Went poorly:** the game-day could not exercise the intended failure and
  recovery path; external drill-time probes did not run; no recovery duration
  or aggregate P95 can be calculated.
- **Surprises:** the `.73` host answered with an identity different from the
  checked-in drill inventory, and both edge targets had zero PDB disruption
  allowance despite healthy read-only cluster observations.

## Recovery and closure

- **Mitigation:** the fail-closed tool stopped each plan before mutation. The
  operator did not weaken PDB protection, rename a host ad hoc, or attempt a
  manual recovery.
- **Recovery:** not applicable to runtime service; the exercise ended with the
  observed native cluster unchanged. Read-only checks recorded the safe
  baseline, with no claim that a failure had recovered.
- **Validation:** all three plan outcomes and the sanitized status record were
  reviewed against the native failure-drill safety contract. Evidence refs are
  `DRILL-CONTROL-20260810T154609.062Z`,
  `DRILL-EDGE03-20260810T155026.177Z`, and
  `DRILL-EDGE02-20260810T155056.958Z`.
- **Recovery objective:** `not measured`; no scenario reached NotReady/Ready
  timing. The six-minute P95 objective remains unproven.
- **Rollback/expiry:** no temporary production change existed; no rollback was
  required.

## SLO and error-budget context

- **Service SLO:** 99% availability over rolling 30 days; no SLA.
- **Measurement:** unknown for this exercise. The external status run was a
  pre-window observation and the local edge snapshot was not a valid SLO
  window.
- **Interpretation:** unknown; do not convert the HTTP-200 snapshot or blocked
  drill plans into availability evidence.
- **Separate drill objective:** P95 recovery under 6 minutes for approved
  isolated controlled drills only; no measurement was produced here.

## Follow-ups

Each item is represented by one GitHub issue with one accountable owner and an
objective validation condition. Issue creation is tracking work, not approval
to mutate production.

| ID | Action / system improvement | Owner | Due | Validation/evidence | Status |
|---|---|---|---|---|---|
| F1 | Resolve the `.73` host identity discrepancy through the reviewed host-inventory path, then rerun the read-only `control-plane-01` plan. | `@macel94` | TBD — schedule with host maintenance | A sanitized plan report passes the identity gate with the expected node identity; link report ID and UTC timestamp. [Issue #5](https://github.com/macel94/belacca-platform/issues/5) | open |
| F2 | Review Longhorn InstanceManager PDB/drain protection through the owning GitOps/change process without bypassing protection. | `@macel94` | TBD — review before runtime drill | Reviewed change or documented no-change decision, followed by a passing read-only plan; link commit/issue and report source IDs/timestamps. [Issue #6](https://github.com/macel94/belacca-platform/issues/6) | open |
| F3 | After prerequisites pass, execute one approved native scenario and attach durable external evidence. | `@macel94` | TBD — after F1/F2 | Sanitized report records cordon, drain, reboot, NotReady, Ready, uncordon, convergence, and external synthetic timestamps; only then assess the six-minute objective. [Issue #7](https://github.com/macel94/belacca-platform/issues/7) | open |

## Review and closure

- **Review findings:** impact and evidence boundaries are complete; detection,
  mitigation, and exercise closure are linked to source IDs/timestamps; runtime
  recovery and SLO claims are explicitly marked unknown; follow-ups have one
  owner each and objective validation criteria.
- **Communications/publication:** sanitized internal platform record; no raw
  command output or private telemetry published.
- **Closure decision:** reviewed and closed as a successful fail-closed
  rehearsal. The runtime-drill acceptance remains open and is tracked by F1–F3.
- **Closed by and UTC time:** Planning/Follow-up Lead, 2026-08-10 UTC.
