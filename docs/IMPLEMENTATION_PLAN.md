# Implementation Plan

## Current baseline

The core finance workflow is implemented and tested: provider-neutral AI, transaction/Gmail/document ingestion, review resolution, financial types, budgets, reports/date ranges, profile, Gmail scheduling, and a visual React dashboard.

## Recommended next milestones

### 1. Finish visual frontend decomposition

- Split `frontend-react/src/App.tsx` into Dashboard, Transactions, Reports, Profile, Settings, Help, shared chart/card, and API modules.
- Preserve all existing API calls and state behavior.
- Add React component tests for filters, review actions, errors, and empty states.

**Acceptance:** same user behavior, smaller components, frontend build passes, key flows have tests.

### 2. Filter-aware export

- Let CSV/JSON export accept the active transaction/report filters.
- Add file naming that includes the selected range.
- Keep a full-data export option.

**Acceptance:** exported records match visible filter criteria and are covered by backend tests.

### 3. Production scheduling and deployment readiness

- Replace the in-process scheduler with one singleton worker, cron job, or queue.
- Add structured logging, health checks, deployment environment guidance, and backups.
- Use HTTPS, secure OAuth redirect configuration, and managed secrets.

**Acceptance:** no duplicate sync in multi-worker deployment; scheduled work is observable and recoverable.

### 4. Data quality improvements

- Add source-aware duplicate detection and richer review explanations.
- Provide an optional transaction edit/delete/audit trail.
- Add category rules and recurring-transaction recognition, always with user control.

**Acceptance:** no silent rewrite of confirmed historical records; every automated rule can be reviewed/disabled.

### 5. Optional multi-user evolution

- Only if product scope changes: add authentication, user-scoped collections, authorization, encrypted per-user tokens, data isolation, and migration plan.

**Acceptance:** every query is scoped by user identity and existing single-user data can migrate safely.

## Delivery process for each change

1. Inspect relevant code/tests and state the smallest safe change.
2. Implement backend contracts before dependent frontend behavior.
3. Add or update tests.
4. Run backend tests and frontend build.
5. Provide manual test steps, expected results, and rollback notes.

## Explicit decisions to preserve

- Single-user scope unless requirements change.
- No Ollama integration.
- Provider-neutral AI boundary; avoid provider-specific routes or filenames for new code.
- Human review before uncertain AI-derived financial records affect totals.
