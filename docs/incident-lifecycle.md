# Incident lifecycle

This is the small-platform incident process for `belacca-platform`. It adapts
Google SRE incident-management and blameless-postmortem practices to the
services and evidence available here. It is a coordination and documentation
process, not an automation or approval system.

## Non-negotiable boundary

- The incident record is **sanitized**. Never paste secrets, secret data,
  passwords, tokens, API keys, credentials, authorization headers/cookies,
  player data, user identifiers, or unredacted private telemetry (raw private
  logs, traces, dashboard exports, addresses, or query results).
- Link observations to the evidence collector's source IDs and timestamps. Do
  not copy raw command output into an incident record. A source ID is not proof
  that the source was complete or healthy; record its status and limitations.
- The evidence collector is bounded and read-only. It does not declare an
  incident, approve an action, mutate a cluster, or establish availability.
- Incident command coordinates people and decisions; it does not authorize a
  direct cluster mutation. Any production change, including an emergency
  rollback or traffic change, must be human-approved, reviewed, tested where
  possible, and made through the appropriate GitOps repository and Flux path.
  The incident record contains pending actions and approvals, never implicit
  approval.
- Do not put credentials in this repository or use an incident record as a
  runbook for bypassing GitOps. Handle security or privacy events through the
  appropriate private escalation path while retaining only sanitized
  references here.

## Lifecycle and minimum operating rules

1. **Detect and declare.** Confirm the symptom with an independent observation
   where possible, record the first known timestamp, choose a provisional
   severity, and name an Incident Commander (IC). Declare early when impact is
   plausible; severity can be lowered after evidence improves.
2. **Coordinate and stabilize.** The IC keeps one working record and assigns
   Operations, Communications, and Planning/Follow-up leads. Operations
   prioritizes mitigation over root-cause certainty. Every hypothesis has an
   evidence source ID and timestamp, a confidence level, and a next test.
3. **Change safely.** Record proposed actions with owner, risk, approval,
   expiry/rollback, and evidence references. No action is executed from this
   document or by the collector. Production changes go through GitOps review
   and Flux reconciliation; status and approval are recorded separately.
4. **Recover and monitor.** Define the recovery observation and watch long
   enough to distinguish recovery from a transient improvement. Record the
   last known impact and recovery timestamps, or explicitly record that they
   are unknown.
5. **Hand off deliberately.** The outgoing lead states impact, current
   hypothesis, actions in flight, decisions needed, risks, next update time,
   and evidence references. The incoming lead acknowledges the handoff in the
   timeline. Do not infer continuity from an unacknowledged edit.
6. **Close the incident.** The IC records that impact has ended, monitoring is
   in place, actions are either complete or owned, communications are done,
   and a postmortem decision has been made. Closure is not a claim that the
   root cause is known.
7. **Learn.** Write the postmortem when a trigger below applies. Review it
   with the involved roles, give each follow-up one owner and validation
   criterion, and close only when the review and follow-up disposition are
   recorded.

For a small incident one person may temporarily hold multiple roles, but the
record must name the combination and the next handoff. A responder may be the
default IC when declaring, but should delegate as soon as practical.

## Severity levels

Severity is a response level, not a measure of individual fault. Use the
highest applicable level and reassess as evidence changes.

| Level | Objective threshold and response |
|---|---|
| **SEV-1 Critical** | Confirmed complete unavailability of a public service for at least 5 continuous minutes, two or more public services unavailable at once, or an active/credible data-integrity or security event with material risk. IC, Operations, Communications, and Planning/Follow-up are assigned immediately; communicate on a fixed cadence. |
| **SEV-2 Major** | One public service has sustained user-visible failure/degradation for at least 5 minutes without a reliable workaround; a critical monitoring blind spot lasts more than two expected hourly observations; a contained data-integrity/security event is confirmed; or an approved controlled drill misses its recovery objective. Assign an IC and at least Operations plus one of Communications or Planning/Follow-up. |
| **SEV-3 Moderate** | A localized or short user-visible degradation below SEV-2, a monitoring gap of one expected observation, a production intervention without SEV-1/2 impact, or a repeat/noisy operational pattern that needs coordinated follow-up. Name an IC and keep a timeline; add other roles as needed. |
| **SEV-4 Minor / observation** | No user or production impact: an isolated near miss, an evidence-only review, or a disposable baseline. Track it when useful, but do not call it availability evidence, a chaos drill, or a recovery result. |

The five-minute threshold is a coordination threshold for this small platform,
not an SLA. The public objective is 99% availability over a rolling 30-day
window per service and there is no SLA. A short probe or evidence bundle cannot
establish that objective. The separate controlled-drill recovery contract,
evidence fields, and P95 calculation are in
[`controlled-drill-recovery.md`](controlled-drill-recovery.md).

## Objective postmortem triggers

Open a postmortem decision record for **any** of the following; the IC or any
stakeholder may also request one. “Unknown” evidence does not waive a trigger.

1. **User-facing critical failure:** any SEV-1, or a confirmed public service
   failure/degradation meeting the SEV-1/SEV-2 duration or scope threshold.
2. **Monitoring failure:** the external hourly observation is missing or stale
   for more than two consecutive expected observations, or monitoring is
   unable to detect a suspected incident; one missed observation is at least a
   SEV-3 review item.
3. **Data integrity or security event:** any suspected or confirmed corruption,
   loss, unauthorized access/exposure, authentication bypass, or integrity
   mismatch. Do not include sensitive details in this repository.
4. **Recovery objective miss:** an approved isolated controlled drill has an
   aggregate recovery P95 of 6 minutes or more once repeated measurements are
   available, or an individual recovery exceeds 6 minutes and therefore needs
   review. The disposable capacity baseline is not a drill and cannot prove
   this objective.
5. **Repeat or noisy incident:** two incidents with the same failure signature
   in 30 days, or three human-actionable pages/alerts with the same signature
   in seven days. Record the alert-quality follow-up even when user impact is
   below SEV-2.
6. **Material intervention:** a human-approved production rollback, traffic
   change, or other production mutation, even if service impact was brief.

A postmortem trigger causes documentation and learning work; it does not make
an unverified hypothesis a root cause. Security/privacy handling may require a
private companion record with only a sanitized reference here.

## Roles and handoffs

- **Incident Commander (IC):** owns the 3Cs (coordinate, communicate, control),
  sets severity and cadence, assigns roles, makes the incident state legible,
  and decides when closure criteria are met. The IC does not perform every
  technical action.
- **Operations Lead (OL):** owns technical investigation, mitigation,
  recovery checks, and the evidence-linked action list. OL reports observations
  and hypotheses, not unsupported certainty.
- **Communications Lead (CL):** owns accurate internal and public/stakeholder
  updates, audience and cadence, impact wording, and correction of stale or
  unverified claims. Never publish private telemetry or player data.
- **Planning/Follow-up Lead (PFL):** owns the timeline, decision and handoff
  log, evidence index, postmortem draft, follow-up owners, due dates, and
  validation/closure tracking. For a small event this role can be combined with
  IC or CL, but must still be explicit.

A handoff is a timeline event, not merely a changed name: record outgoing and
incoming roles, UTC timestamp, state/impact, active actions, risks, next update,
and acknowledgement.

## Sanitized incident-state template

Copy the marked block into a new record. Replace bracketed values; remove
unfilled optional lines before review. Keep source IDs and UTC timestamps, not
raw output.

<!-- TEMPLATE:INCIDENT-STATE:START -->

# Incident state — [INCIDENT-ID] — [short sanitized title]

- **State:** [declared | active | monitoring | resolved | closed]
- **Severity:** [SEV-1 | SEV-2 | SEV-3 | SEV-4] — [why, using an objective threshold]
- **Declared at (UTC):** [timestamp or `unknown`]
- **Last updated at (UTC):** [timestamp]
- **Incident Commander:** [name/role]
- **Operations Lead:** [name/role]
- **Communications Lead:** [name/role]
- **Planning/Follow-up Lead:** [name/role]
- **Channel/record location:** [sanitized location; no credentials or private exports]

## Current impact

- **Affected service/journey:** [public service or `none observed`]
- **Impact:** [what users can/cannot do; no player data or identifying detail]
- **Scope and start:** [scope, first known UTC timestamp, or `unknown`]
- **Current status:** [impact now, workaround if any, next update UTC]
- **Availability/SLO context:** [measurement window, SLI result, budget consumed,
  or `unknown`; a bundle alone is not an availability measurement]

## Evidence index

| Source ID | Evidence timestamp (UTC) | Status/completeness | Sanitized observation or link |
|---|---|---|---|
| [source-id] | [timestamp] | [ok/failed/incomplete] | [bounded observation; no raw output] |

## Timeline (UTC)

| Time | Event/decision | Actor/role | Evidence refs |
|---|---|---|---|
| [timestamp] | [observation, mitigation, handoff, update, or decision] | [role] | [source-id(s)] |

## Hypotheses and tests

| ID | Hypothesis (not fact) | Confidence | Evidence source IDs + timestamps | Next test / falsifier |
|---|---|---|---|---|
| H1 | [sanitized statement] | [low/medium/high] | [source-id @ timestamp] | [bounded read-only test or `not available`] |

## Change control

- **Rule:** No direct cluster mutation. No approval is implied by this record or
  evidence bundle. Production changes require human approval and a reviewed,
  tested GitOps change through Flux.
- **Pending action:** [action, owner, risk, approval state, expiry/rollback,
  evidence refs; use `none` when no action is proposed]

## Handoffs and communications

- **Handoff:** [UTC time, outgoing role/person, incoming role/person,
  acknowledgement, state summary]
- **Update log:** [audience, UTC time, sanitized statement, next update]

## Closure criteria

Close only when all applicable items are true:

- [ ] user impact ended or is explicitly recorded as unknown;
- [ ] recovery was observed with source IDs/timestamps, or limitation recorded;
- [ ] monitoring is active and its evidence is not being mistaken for proof of health;
- [ ] actions are complete, cancelled with reason, or owned with due dates;
- [ ] required communications were sent and corrected if needed;
- [ ] postmortem trigger decision is recorded and a postmortem is linked when required;
- [ ] IC and Planning/Follow-up Lead reviewed closure.

<!-- TEMPLATE:INCIDENT-STATE:END -->

## Blameless postmortem template

Use this for a triggered event. The goal is learning and system improvement,
not assigning fault. Assume people acted with good intent and the information
available at the time. Do not put secrets, player data, tokens, or unredacted
private telemetry in the document.

<!-- TEMPLATE:POSTMORTEM:START -->

# Blameless postmortem — [INCIDENT-ID] — [sanitized title]

- **Incident state record:** [link/ID]
- **Severity and trigger(s):** [level and objective trigger]
- **Incident window (UTC):** [start — recovery/unknown]
- **Review status:** [draft | reviewed | closed]
- **Review date/participants:** [UTC date and roles; no private identities required]

## Impact

- **User/service impact:** [scope, duration, affected journeys, or explicitly none]
- **Detection-to-declaration:** [duration or unknown]
- **Business/data/security impact:** [sanitized statement; private companion ref if needed]

## Detection and response

- **How detected:** [source ID, external observation, or human report]
- **What was not detected:** [blind spots and limitations]
- **Response roles and handoffs:** [IC, OL, CL, PFL and UTC handoffs]

## Timeline (UTC)

| Time | Observation, decision, action, or communication | Evidence refs |
|---|---|---|
| [timestamp] | [sanitized event] | [source-id @ timestamp] |

## Contributing factors and hypotheses

- **Contributing factors:** [system, design, process, dependency, or signal factors]
- **Confirmed cause:** [only what evidence supports; `not established` is valid]
- **Rejected/remaining hypotheses:** [hypothesis, evidence, confidence, next test]
- **Blameless check:** [describe system conditions; do not name a person/team as the cause]

## What went well / poorly

- **Went well:** [detection, coordination, mitigation, recovery, or communication]
- **Went poorly:** [gaps in signal, tooling, ownership, procedure, or resilience]
- **Surprises:** [observations that changed the plan]

## Recovery

- **Mitigation and recovery:** [actions, GitOps change IDs if applicable, and UTC times]
- **Validation:** [post-recovery checks and source IDs]
- **Recovery objective:** [approved drill result, or `not a drill/not measured`]
- **Rollback/expiry:** [how temporary actions ended; no direct-mutation instructions]

## SLO and error-budget context

- **Service SLO:** 99% availability over rolling 30 days; no SLA.
- **Measurement:** [SLI, valid window, bad/total events, availability, budget
  consumed, and source/reference; `unknown` if not measured]
- **Interpretation:** [within/breached/unknown; explain sampling limits]
- **Separate drill objective:** P95 recovery under 6 minutes for approved
  isolated controlled drills only. Never derive it from availability arithmetic,
  a short load run, or an evidence snapshot.

## Follow-ups

Every item needs one accountable owner, a due date or explicit `TBD`, and a
validation condition. Follow-ups propose work; they are not approvals.

| ID | Action / system improvement | Owner | Due | Validation/evidence | Status |
|---|---|---|---|---|---|
| F1 | [specific prevention/detection improvement] | [role] | [UTC/TBD] | [test, review, or source ref] | [open/closed] |

## Review and closure

- **Review findings:** [completeness, impact, evidence linkage, depth, and follow-up quality]
- **Communications/publication:** [sanitized audience and location]
- **Closure decision:** [reviewed/closed or remaining blockers]
- **Closed by and UTC time:** [role/time]

<!-- TEMPLATE:POSTMORTEM:END -->

## Completed sanitized example (not a production incident)

**Classification: documentation-only SEV-4/non-incident example based on the
recent disposable capacity-baseline definition.** The parent workspace has one executed disposable run with an uploaded artifact,
but it was a capacity baseline, not a chaos drill or production event. It does
not prove the public availability SLO or the six-minute recovery objective.

- **Record:** `EXAMPLE-CAPACITY-BASELINE-31286754660`
- **Execution reference:** GitHub Actions run `31286754660`, head commit
  `3f791c6`, with the artifact retained by the workflow for seven days.
- **Evidence refs:**
  - `RUN-31286754660` — the workflow run and uploaded aggregate/resource
    artifact; source timestamp is the run's recorded execution time.
  - `DOC-BASELINE-PLAN` — `cloudnativepong/docs/CAPACITY-CHAOS-PLAN.md`,
    referenced by parent commit `bbb2bd9`; defines loopback-only disposable
    scope and says its evidence cannot prove availability or drill P95.
  - `DOC-BASELINE-WORKFLOW` —
    `cloudnativepong/.github/workflows/capacity-experiment.yml`, referenced by
    parent commit `bbb2bd9`; defines bounded artifact collection and exact
    disposable-cluster cleanup.

### Incident-state summary

- **State/severity:** closed as evidence-only, SEV-4; no incident declared.
- **Roles:** IC/OL/CL/PFL are `not assigned` because this was an automated
  disposable baseline, not an incident or failure drill.
- **Impact:** no production impact, public-route traffic, production PVC access,
  player data, or user data is evidenced. The run used a temporary k3d cluster
  and loopback gateway only.
- **Observed result:** 3/3 bounded journeys passed with no failure codes;
  health p95 3ms, create p95 2039ms, join p95 5ms, WebSocket p95 38ms, and
  cleanup p95 3074ms. Node snapshots showed 2–3% CPU and 1–4% memory. These
  values are baseline evidence for this disposable run only.
- **Timeline:** the run created the exact run-ID-derived cluster, built/imported
  local images, deployed the test overlay, ran three sequential journeys,
  uploaded aggregate/resource evidence, and deleted the exact cluster.
- **Hypothesis H1:** the tested disposable topology can complete three bounded
  journeys sequentially under the recorded conditions — confidence **high**;
  ref `RUN-31286754660`. This is not a production capacity claim.
- **Hypothesis H2:** public availability and controlled-drill recovery remain
  unknown — confidence **high**; refs `RUN-31286754660` and `DOC-BASELINE-PLAN`.
- **Change control:** no production approval or mutation was performed. Any
  future production change remains GitOps-only.
- **Closure:** the artifact and limitations are recorded. Repeated baselines,
  resource-pressure tests, and one-fault-at-a-time recovery drills are still
  required. The six-minute objective is **not proven**.

This example demonstrates how to record absence of evidence without converting
an implementation plan into an operational claim. Replace it with a real,
human-reviewed record if a suitable isolated exercise is later performed.

## References

- [Google SRE incident response](https://sre.google/workbook/incident-response/)
- [Google SRE postmortem culture](https://sre.google/sre-book/postmortem-culture/)
- [Google SRE implementing SLOs](https://sre.google/workbook/implementing-slos/)
- [Incident evidence boundary](incident-evidence.md)
