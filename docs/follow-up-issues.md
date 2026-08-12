# Incident follow-up issues

Every corrective action from an incident or controlled game-day becomes a
separate GitHub issue in `macel94/belacca-platform` using the
[Incident follow-up form](../.github/ISSUE_TEMPLATE/follow-up.yml). This makes
ownership and validation searchable without turning a postmortem into an
approval queue.

## Required issue fields

- Link the sanitized incident-state record and reviewed postmortem.
- Describe one concrete prevention, detection, response, or resilience action.
- Name exactly one accountable owner (role or GitHub handle).
- Set a UTC due date, or write `TBD` with a reason and a next review date.
- Define objective validation evidence: a test, review, metric, or sanitized
  source ID plus UTC timestamp. “Deployed” or “looks fixed” is not validation.
- Describe rollout, rollback, expiry, and the owning GitOps repository for any
  production change. The issue is not approval to mutate production.
- Close only after the owner links the validation evidence and the Planning /
  Follow-up Lead records the result in the postmortem.

## Evidence and privacy

Use source IDs and evidence timestamps, sanitized workflow links, and commit or
issue URLs. Never paste command output. Do not include secrets, player data,
tokens, credentials, addresses/private identifiers, or unredacted private
telemetry. Sensitive security/privacy details belong in a private companion
record with only a sanitized reference here.

## Lifecycle

1. Planning/Follow-up Lead opens one issue per action after postmortem review.
2. Owner proposes the implementation and obtains the normal review/approval in
   the owning repository.
3. Owner links deterministic validation evidence and requests review.
4. IC or Planning/Follow-up Lead confirms the acceptance criterion and updates
   the postmortem row to `closed`; only then is the issue closed.
5. Overdue or blocked issues are re-planned; they are not silently marked done.

The GitHub CLI, API, and automation are intentionally not invoked by the
incident-record tool. An operator must review and create each issue explicitly.
