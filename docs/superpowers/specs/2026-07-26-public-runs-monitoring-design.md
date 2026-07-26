# Public Runs Monitoring Design

**Date:** 2026-07-26  
**Status:** Approved for implementation planning

## Context

Published Fortune conversations execute through the configured Published App agent, its Skill, the selected DeepSeek model, and `AgentEngine`. They do not appear in the existing Agent session or run views because public traffic deliberately uses an isolated storage domain:

- Managed Agent data: `workspace/sessions/` and `workspace/runs/`
- Anonymous Published App data: `workspace/public_sessions/{session_id}/`

Public session content expires after the configured TTL, normally 24 hours. The current public session repository stores session metadata, input, chart data, and messages, but it neither exposes management APIs nor persists operational run events. Administrators therefore cannot inspect public conversations or diagnose public model failures from Workbuddy.

## Goals

- Give authenticated Workbuddy administrators a dedicated view of anonymous Published App sessions.
- Show the conversation and a sanitized operational event timeline for each public run.
- Mask birth data by default and reveal it only after an explicit administrator action.
- Let an administrator permanently delete an eligible anonymous session.
- Retain non-identifying cumulative operational totals after session content expires.
- Preserve the isolation between public sessions and ordinary Agent sessions and runs.

## Non-Goals

- Do not merge public sessions into `/api/sessions` or `/api/runs`.
- Do not expose the management APIs through the Fortune public domain.
- Do not retain session content longer than the existing public session TTL.
- Do not build daily, monthly, or other time-series analytics.
- Do not backfill or estimate permanent counters from historical session directories.
- Do not store or display raw IP addresses.
- Do not add a live management SSE connection; polling is sufficient.

## Architecture

Public monitoring is a separate management domain named **Public Runs**. It reuses the existing public session directory as the lifecycle boundary while adding a management router, sanitized event persistence, and a permanent aggregate metrics repository.

```text
Fortune client
    |
    v
Public runtime service -----> AgentEngine / configured model
    |                              |
    |                              v
    +---- session content     sanitized run events
    |     public_sessions/    public_sessions/{session}/runs/
    |
    +---- cumulative counters
          public_metrics.json

Authenticated Workbuddy administrator
    |
    v
/api/public-runs -----> public session repository + metrics repository
```

The components have distinct responsibilities:

- The public runtime service executes reports and questions and emits lifecycle events.
- The public session repository owns TTL-bound session content, summaries, detail reads, events, and deletion.
- The public metrics repository owns permanent counters and contains no session-level data.
- The management router authenticates administrators, validates filters, and returns safe response models.
- The frontend page presents cumulative totals, a session table, and a detail drawer.

## Storage

### TTL-Bound Session Data

Each session remains under its existing directory:

```text
workspace/public_sessions/{session_id}/
  session.json
  input.json
  chart.json
  messages.json
  runs/
    {run_id}.jsonl
```

Run event files share the session's TTL. Visitor deletion, administrator deletion, or TTL cleanup removes the whole directory, including messages and event files.

Historical sessions created before event collection remain readable. Their event view reports `historical_events_unavailable`; it does not infer or fabricate events from messages.

### Permanent Aggregate Metrics

Permanent counters are stored in:

```text
workspace/public_metrics.json
```

The file is versioned and grouped by `app_id`. Cross-application totals are derived when the API reads the per-app counters, avoiding a second persisted copy that could drift.

```json
{
  "version": 1,
  "apps": {
    "fortune": {
      "sessions_created": 1250,
      "reports_completed": 1180,
      "reports_failed": 22,
      "questions_completed": 2634,
      "questions_failed": 41,
      "runs_started": 3877,
      "runs_completed": 3814,
      "total_duration_ms": 9468200,
      "admin_deletions": 8,
      "visitor_deletions": 316,
      "ttl_cleanups": 901,
      "errors": {
        "MODEL_TIMEOUT": 19,
        "MODEL_RATE_LIMITED": 11
      }
    }
  }
}
```

Updates follow the existing atomic JSON store pattern: acquire the repository lock, read and modify the current value, write a temporary file, and atomically replace the target. This prevents concurrent requests in the current process from losing increments. The public runtime deployment remains single backend process; a future multi-process deployment must replace or augment this with an inter-process lock or transactional store before increasing the worker count.

The metrics file must never contain session IDs, dates or trend buckets, messages, names, birth data, Cookie values, owner identifiers, raw IP addresses, or IP hashes.

## Run Event Model

One report generation or question creates one `run_id`. Events use monotonically increasing sequence numbers within that run and are appended as JSON Lines.

Normal event sequence:

```text
run.started
agent.started
model.started
model.completed
agent.completed
run.completed
```

Failure paths end with `model.failed`, `agent.failed`, or `run.failed`. A run with a start event and no terminal event is exposed as `interrupted`.

Each persisted event is limited to operational metadata:

```json
{
  "run_id": "run_...",
  "sequence": 3,
  "timestamp": "2026-07-26T12:00:00Z",
  "type": "model.completed",
  "mode": "report",
  "duration_ms": 2840,
  "model_id": "deepseek-v4-flash",
  "error_code": null
}
```

The event writer must not persist user or model messages, birth data, chart data, prompts, API keys, headers, Cookies, raw IP addresses, or IP hashes. `messages.json` remains the only canonical conversation copy.

Errors are normalized to a finite set of safe codes, initially:

```text
MODEL_TIMEOUT
MODEL_AUTH_FAILED
MODEL_RATE_LIMITED
MODEL_RESPONSE_INVALID
ENGINE_FAILED
SESSION_EXPIRED
QUOTA_EXCEEDED
```

Pre-execution rejections such as an expired session or exhausted quota may be returned to the caller but do not create a run or increment run failure counters. Raw exception messages and stack traces are never persisted in event files or returned by management APIs.

## Metrics Semantics

- Increment `sessions_created` only after a session is successfully created.
- Increment `runs_started` after a request is accepted and receives a `run_id`.
- On successful report completion, increment `reports_completed`, `runs_completed`, and `total_duration_ms`.
- On successful question completion, increment `questions_completed`, `runs_completed`, and `total_duration_ms`.
- On execution failure, increment the corresponding report or question failure counter and one safe error-code counter.
- Do not count validation, quota, or expiry rejections that occur before execution as run failures.
- Count administrator deletion, visitor deletion, and TTL cleanup only after data is actually removed.
- Deletion causes are mutually exclusive; retries and deletion of absent sessions do not increment counters.
- Calculate average duration at read time as `total_duration_ms / runs_completed`.

Counters begin at deployment. Existing session directories may appear in the list, but they do not contribute guessed historical totals.

## Management API

All endpoints use the existing Workbuddy management authentication and authorization. They are mounted on the management backend only.

```text
GET    /api/public-runs
GET    /api/public-runs/stats
GET    /api/public-runs/{session_id}
DELETE /api/public-runs/{session_id}
```

### Session List

```text
GET /api/public-runs
  ?app_id=fortune
  &status=active|running|completed|failed|expired
  &query=<session_id>
  &limit=50
  &cursor=<opaque_cursor>
```

Results are ordered by most recent activity. Cursor pagination provides stable traversal while new sessions arrive.

```json
{
  "items": [
    {
      "session_id": "pub_...",
      "app_id": "fortune",
      "status": "active",
      "created_at": "...",
      "updated_at": "...",
      "expires_at": "...",
      "remaining_questions": 2,
      "message_count": 6,
      "run_count": 3,
      "last_run_status": "completed"
    }
  ],
  "next_cursor": "...",
  "refreshed_at": "..."
}
```

The list never includes birth data or visitor identifiers.

### Session Detail

The default request returns masked birth data, chart summary, conversation messages, and sanitized run events:

```text
GET /api/public-runs/{session_id}
```

An explicit request returns complete business birth details:

```text
GET /api/public-runs/{session_id}?include_sensitive=true
```

Sensitive data is not included in the initial response or embedded in the initial frontend state. Even the sensitive response excludes raw IP addresses, IP hashes, Cookies, internal owner identifiers, secrets, prompts, and headers.

### Statistics

`GET /api/public-runs/stats` returns permanent cumulative values per app and a derived all-app total. It returns neither trends nor session identifiers.

### Deletion

`DELETE /api/public-runs/{session_id}` deletes the entire session directory under a session-level lock and returns `204`. It does not refund consumed daily quota. If an uncommitted quota reservation still exists, it is released consistently with existing visitor deletion behavior.

Deletion of a running session is rejected with `409 SESSION_RUNNING`; the administrator retries after the run reaches a terminal state. Deletion of an absent or already cleaned session returns `404`. Concurrent administrator, visitor, and TTL deletion attempts can remove and count the session only once.

## Session Status

The backend computes status; the frontend does not infer it:

- `active`: the session is valid, no request is running, and additional interaction remains possible.
- `running`: a report or question is currently executing.
- `completed`: a report exists and the question allowance is exhausted.
- `failed`: initial report generation failed and no usable report exists.
- `expired`: the TTL has passed but cleanup has not removed the directory yet.

Once TTL cleanup removes an expired directory, it disappears from the API and list.

## Administrator UI

Add a management route at `/public-runs` and a sidebar item named **公开运行**, separate from **运行记录**.

The page uses the approved **运营总览 + 会话表格** layout and follows Workbuddy's existing light, restrained, dense operational design language:

- Cumulative statistic tiles for sessions, successful runs, failed runs, and average duration.
- App and status filters plus session ID search.
- A dense session table ordered by recent activity.
- Automatic list refresh every 15 seconds and a manual refresh action.
- A right-side detail drawer opened by selecting a row.

The drawer contains session status, app, remaining question allowance, creation and expiry times, masked birth information, chart summary, and two tabs:

- **对话** shows the canonical user and assistant messages.
- **运行事件** shows run grouping, stages, duration, status, and safe error codes.

The administrator must click **显示敏感资料** before the frontend requests unmasked birth fields. Revealed data remains visible only for the current drawer and session. Closing the drawer or switching sessions resets to the masked state.

The destructive action **删除这条匿名会话** uses a confirmation dialog that states deletion is irreversible and consumed quota is not refunded.

## Refresh and Error Handling

- While a drawer is open, polling refreshes the selected session's metadata, messages, and events as well as the list.
- Polling preserves the selected row, current tab, scroll position where practical, and current sensitive reveal state for that open drawer.
- Closing or switching the drawer always resets sensitive reveal state.
- An automatic refresh failure preserves existing content and displays a non-blocking error indicator.
- A manual refresh failure displays an explicit retryable notification.
- If the open session expires or is deleted, the drawer reports that it is unavailable, closes, and refreshes the list.
- A `409 SESSION_RUNNING` deletion response explains that the current run must finish.
- Existing management behavior handles `401` and `403` responses.
- Unknown backend failures expose only a generic message and safe error code, never stack traces.
- The polling timer is stopped when the view unmounts.

## Privacy and Network Boundaries

- Administrators can read conversations because operational support is the purpose of this management surface.
- Birth data is masked by default and fetched unmasked only on explicit request.
- Raw IP addresses are neither stored nor displayed.
- Existing IP hashes used for anonymous abuse controls are never returned by these APIs or copied into events or metrics.
- Fortune Nginx continues to proxy only the published public API paths. `/api/public-runs` must return `404` from the Fortune domain.
- Management responses must use explicit safe response models rather than serializing repository objects directly.

## Verification Strategy

### Backend

- Repository tests cover summary listing, detail loading, event append/order, atomic metric increments, and deletion.
- API tests cover filters, search, cursor pagination, default masking, explicit sensitive reads, and `404`/`409` deletion behavior.
- Runtime tests cover successful and failed reports and questions, timeouts, model errors, and interrupted event sequences.
- Lifecycle tests prove that administrator deletion, visitor deletion, and TTL cleanup are counted exactly once under competing attempts.
- Quota tests prove consumed quota is not refunded and only an uncommitted reservation can be released.
- Historical-session tests prove messages remain readable while unavailable event history is represented honestly.
- Privacy tests recursively inspect API responses, event files, and `public_metrics.json` for prohibited fields and values.

The required metric invariants are:

```text
successful run   -> started + completed + duration
failed run       -> started + failure + safe error code
pre-run rejection -> no run counter changes
admin deletion   -> admin_deletions only
competing cleanup -> exactly one deletion reason
```

### Frontend

- Component tests cover statistic tiles, filters, search, pagination, loading, empty, and error states.
- Timer tests cover the 15-second refresh and cleanup on unmount.
- Drawer tests cover masked defaults, explicit reveal, reset on close/switch, both tabs, and missing historical events.
- Deletion tests cover confirmation, success, `404`, and `409`.
- Refresh tests prove stale data remains visible during transient polling failures.

### Browser Acceptance

Run the full local Fortune and Workbuddy stack and produce a real report plus at least one question. Verify desktop and mobile viewports for:

- No table, drawer, control, long ID, error code, or message overflow.
- Stable table and drawer state during polling.
- Correct completed, failed, running, and historical displays.
- Sensitive values absent from the initial HTML, default API response, and browser logs.
- Correct masked-to-unmasked transition and reset behavior.
- Fortune public domain isolation for `/api/public-runs`.

Run the existing backend and frontend suites to catch regressions in managed Agent sessions, normal runs, Fortune conversations, model selection, and public quota behavior.

## Rollout

The feature ships on the existing `feat/fortune-published-app` branch and open pull request. Permanent counters begin at deployment. Older TTL-bound sessions are visible without fabricated events. No production deployment is expected until the user reviews and merges the pull request; the existing deployment workflow then publishes the merged code.

## Approved Decisions

- Separate Public Runs management domain.
- Operations overview plus session table and right-side drawer.
- Administrator conversation access with birth data masked by default.
- No raw IP storage or display.
- Administrator deletion without consumed quota refund.
- 15-second polling plus manual refresh; no management SSE.
- Permanent cumulative totals only; no trends.
- TTL-bound run events and permanent non-identifying metrics.
- No event or metric backfill for historical sessions.
