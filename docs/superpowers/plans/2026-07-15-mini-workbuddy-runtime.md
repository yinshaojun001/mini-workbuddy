# Mini-workbuddy Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persisted conversations, streaming model execution, Skill-aware tool calling, explicit write/command approvals, run history, and a complete Agent run interface.

**Architecture:** The runtime composes immutable run context from management resources, calls an OpenAI-compatible adapter, and reduces each model/tool/approval transition into ordered append-only events. An in-memory approval broker pauses live tasks while persisted approval records and run events keep the UI auditable.

**Tech Stack:** FastAPI, Pydantic 2, httpx streaming, asyncio, SSE, JSONL, Vue 3, Pinia, Fetch streaming, Vitest, Playwright.

---

### Task 1: Add sessions, messages, run events, and recovery

**Files:**
- Create: `backend/app/sessions/schemas.py`
- Create: `backend/app/sessions/repository.py`
- Create: `backend/app/sessions/router.py`
- Create: `backend/app/runs/schemas.py`
- Create: `backend/app/runs/repository.py`
- Create: `backend/app/runs/router.py`
- Create: `backend/tests/runtime/test_session_api.py`
- Create: `backend/tests/runtime/test_run_repository.py`
- Modify: `backend/app/main.py`

- [ ] Test session CRUD, append-only message order, run sequence monotonicity, malformed trailing-line tolerance, and startup conversion of `running` runs to `interrupted`.
- [ ] Implement session JSON plus message JSONL repositories and run JSONL event repositories.
- [ ] Expose session/message/run history routes with pagination bounds.
- [ ] Run focused and complete backend tests; expect pass.
- [ ] Commit with `git commit -m "feat: persist sessions and run events"`.

### Task 2: Implement prompt assembly and OpenAI-compatible streaming adapter

**Files:**
- Create: `backend/app/runtime/context.py`
- Create: `backend/app/runtime/events.py`
- Create: `backend/app/runtime/model_adapter.py`
- Create: `backend/app/runtime/openai_stream.py`
- Create: `backend/tests/runtime/test_context.py`
- Create: `backend/tests/runtime/test_openai_stream.py`

- [ ] Test stable prompt ordering, enabled selected Skill injection, disabled/missing resource errors, tool JSON schemas, fragmented SSE lines, text deltas, fragmented tool arguments, provider error events, and `[DONE]` handling.
- [ ] Implement immutable `RunContext`, skill delimiters, OpenAI-compatible request conversion, and normalized streamed model output types.
- [ ] Run runtime adapter tests; expect pass.
- [ ] Commit with `git commit -m "feat: stream model responses"`.

### Task 3: Implement approval broker and Agent tool loop

**Files:**
- Create: `backend/app/runtime/approvals.py`
- Create: `backend/app/runtime/engine.py`
- Create: `backend/app/runtime/router.py`
- Create: `backend/tests/runtime/test_approvals.py`
- Create: `backend/tests/runtime/test_engine.py`
- Modify: `backend/app/main.py`

- [ ] Test immediate reads, pending writes/commands, allow once, reject, duplicate resolution conflict, disconnect behavior, tool authorization failures, disabled tools, provider failure, cancellation, eight-round limit, event persistence, and final assistant messages.
- [ ] Implement `ApprovalBroker` with persisted records and one `asyncio.Future` per live approval.
- [ ] Implement the deterministic Agent loop against a fake adapter interface; never place provider HTTP details in the loop.
- [ ] Expose run SSE creation/cancellation and approval resolution routes.
- [ ] Run runtime and complete backend tests; expect pass.
- [ ] Commit with `git commit -m "feat: run agents with tool approvals"`.

### Task 4: Build conversation streaming state and UI

**Files:**
- Create: `frontend/src/api/sessions.ts`
- Create: `frontend/src/api/runtime.ts`
- Create: `frontend/src/stores/runtime.ts`
- Create: `frontend/src/views/runtime/AgentRunView.vue`
- Create: `frontend/src/components/runtime/SessionList.vue`
- Create: `frontend/src/components/runtime/ConversationTimeline.vue`
- Create: `frontend/src/components/runtime/MessageComposer.vue`
- Create: `frontend/src/components/runtime/RuntimeContext.vue`
- Create: `frontend/src/components/runtime/ToolCallItem.vue`
- Create: `frontend/src/components/runtime/ApprovalItem.vue`
- Create: `frontend/src/stores/runtime.test.ts`
- Modify: `frontend/src/router/index.ts`

- [ ] Test event deduplication/order, text delta reduction, reconnection from last sequence, pending approval state, allow/reject transitions, composer lock behavior, and completed/error states.
- [ ] Implement Fetch-based SSE parsing for POST run requests and Pinia state reduction.
- [ ] Build the desktop three-column run workspace and mobile drawers with stable message widths and auto-scroll that stops when the user reads history.
- [ ] Render tool requests, results, approvals, errors, and interruption as timeline items rather than toasts.
- [ ] Run frontend tests and production build; expect pass.
- [ ] Commit with `git commit -m "feat: build agent run workspace"`.

### Task 5: Build run history, dashboard live state, and end-to-end execution tests

**Files:**
- Create: `frontend/src/api/runs.ts`
- Create: `frontend/src/stores/runs.ts`
- Create: `frontend/src/views/runs/RunsView.vue`
- Create: `frontend/src/views/runs/RunDetailView.vue`
- Create: `frontend/src/components/runs/EventTrace.vue`
- Create: `frontend/e2e/runtime.spec.ts`
- Modify: `frontend/src/views/DashboardView.vue`
- Modify: `frontend/src/router/index.ts`

- [ ] Build run tables and chronological trace details with filters for status, Agent, tool, and approval outcome.
- [ ] Connect the dashboard to live counts and recent events.
- [ ] Add fake-provider E2E flows for read-file completion, approved write completion, rejected command continuation, and interrupted run history.
- [ ] Run backend tests, frontend tests, build, and all Playwright tests; expect pass.
- [ ] Commit with `git commit -m "feat: add runtime observability"`.

### Task 6: Final visual, responsive, accessibility, and documentation verification

**Files:**
- Create: `README.md`
- Create: `backend/.env.example`
- Create: `frontend/e2e/visual.spec.ts`
- Modify: `frontend/src/styles/main.css`
- Modify: `.gitignore`

- [ ] Document `uv sync`, `uv run uvicorn app.main:app --reload`, `npm install`, `npm run dev`, workspace location, provider configuration, tool approvals, and test commands.
- [ ] Add desktop and mobile screenshots for every primary route and assert no horizontal overflow, overlapping controls, blank views, or clipped Chinese labels.
- [ ] Check keyboard navigation, focus visibility, dialog focus trap, form labels, tree semantics, contrast, and reduced motion.
- [ ] Scan frontend source for visible English strings and replace all non-exempt copy with Simplified Chinese.
- [ ] Run `cd backend && uv run pytest`, `cd frontend && npm test -- --run`, `npm run build`, and `npm run test:e2e`; expect all pass.
- [ ] Start both development servers and manually verify model, Skill, Agent, conversation, approval, and history workflows.
- [ ] Commit with `git commit -m "docs: finish mini-workbuddy demo"`.
