# Mini-workbuddy Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the runnable local management application for models, fixed tools, Skills, and Agents with file-backed persistence.

**Architecture:** A FastAPI modular monolith exposes domain REST routers backed by atomic JSON/Markdown repositories. A Vue 3 SPA uses Pinia domain stores and a compact dark-sidebar/light-workspace design. Resource shapes are stable inputs for the runtime phase.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic 2, httpx, pytest, Vue 3, TypeScript, Vite, Pinia, Vue Router, Tailwind CSS 4, Lucide Vue Next, Vitest, Playwright.

---

### Task 1: Scaffold backend and deterministic workspace seed

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/errors.py`
- Create: `backend/app/storage/json_store.py`
- Create: `backend/app/storage/bootstrap.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_bootstrap.py`

- [ ] Write a failing test that starts the application with a temporary `WORKSPACE_DIR` and asserts creation of `models.json`, `tools.json`, `agents.json`, `skills/`, `agents/`, `sessions/`, `runs/`, and `runtime/`.
- [ ] Run `cd backend && uv run pytest tests/test_bootstrap.py -v`; expect failure because the app package does not exist.
- [ ] Add `Settings`, application lifespan bootstrap, uniform `AppError` JSON handling, and an `AtomicJsonStore` that writes to a same-directory temporary file then calls `os.replace`.
- [ ] Seed two keyless model templates, exactly three built-in enabled tools, and the undeletable main Agent. Make bootstrap idempotent.
- [ ] Run `cd backend && uv run pytest tests/test_bootstrap.py -v`; expect all tests to pass.
- [ ] Commit with `git commit -m "feat: scaffold file-backed backend"`.

### Task 2: Implement model configuration and diagnostics

**Files:**
- Create: `backend/app/models/schemas.py`
- Create: `backend/app/models/repository.py`
- Create: `backend/app/models/service.py`
- Create: `backend/app/models/router.py`
- Create: `backend/app/providers/openai_compatible.py`
- Create: `backend/tests/models/test_model_api.py`
- Create: `backend/tests/models/test_model_diagnostics.py`
- Modify: `backend/app/main.py`

- [ ] Write API tests for list/create/update/delete, provider validation, masked secret responses, empty-key preservation, and rejecting deletion of an Agent-bound model.
- [ ] Write diagnostics tests with `httpx.MockTransport` for success, 401, 429, timeout, network error, and malformed JSON.
- [ ] Run the two model test modules; expect route import failures.
- [ ] Implement Pydantic resource/input schemas and repository/service methods. Never serialize `api_key` into response models; return `has_api_key` and `api_key_hint`.
- [ ] Implement DeepSeek and Qwen provider defaults and a minimal `/chat/completions` diagnostic request with explicit error-code mapping.
- [ ] Register `/api/models` CRUD and `/api/models/{id}/test` routes.
- [ ] Run model tests and the complete backend suite; expect pass.
- [ ] Commit with `git commit -m "feat: manage model providers"`.

### Task 3: Implement fixed tools and workspace-bound executors

**Files:**
- Create: `backend/app/tools/schemas.py`
- Create: `backend/app/tools/registry.py`
- Create: `backend/app/tools/executors.py`
- Create: `backend/app/tools/router.py`
- Create: `backend/tests/tools/test_tool_api.py`
- Create: `backend/tests/tools/test_executors.py`
- Modify: `backend/app/main.py`

- [ ] Write tests asserting tools cannot be created/deleted, can be enabled/disabled, and always retain IDs `read_file`, `write_file`, and `run_command`.
- [ ] Write executor tests for normal reads/writes, missing files, binary/oversized reads, `..` traversal, absolute paths outside root, symlink escape, command timeout, output truncation, and secret-free environment construction.
- [ ] Run tool tests; expect import failures.
- [ ] Implement a fixed registry and `PATCH /api/tools/{id}` accepting only `enabled`.
- [ ] Implement `resolve_in_workspace`, asynchronous file executors, and subprocess execution with bounded output and duration metadata.
- [ ] Run tool tests and backend suite; expect pass.
- [ ] Commit with `git commit -m "feat: add protected built-in tools"`.

### Task 4: Implement Skill storage, editing, trees, and safe ZIP import

**Files:**
- Create: `backend/app/skills/schemas.py`
- Create: `backend/app/skills/repository.py`
- Create: `backend/app/skills/importer.py`
- Create: `backend/app/skills/service.py`
- Create: `backend/app/skills/router.py`
- Create: `backend/tests/skills/test_skill_api.py`
- Create: `backend/tests/skills/test_skill_import.py`
- Modify: `backend/app/main.py`

- [ ] Write tests for create/update/list/detail/toggle, mandatory non-empty `SKILL.md`, structured directory trees, safe text previews, and delete conflicts when bound to Agents.
- [ ] Generate ZIP fixtures in tests for root Skill, wrapped Skill, missing manifest, multiple candidates, traversal, absolute paths, symlink entries, duplicate names, too many entries, and excessive expanded size.
- [ ] Run Skill tests; expect failures.
- [ ] Implement directory-backed Skill repositories and atomic metadata/Markdown writes.
- [ ] Implement staged ZIP extraction by inspecting every `ZipInfo` before writing, validating limits, and atomically moving a single Skill root into place.
- [ ] Expose REST routes and multipart `/api/skills/import`.
- [ ] Run Skill tests and backend suite; expect pass.
- [ ] Commit with `git commit -m "feat: manage local skills"`.

### Task 5: Implement Agent resources, prompt files, and bindings

**Files:**
- Create: `backend/app/agents/schemas.py`
- Create: `backend/app/agents/repository.py`
- Create: `backend/app/agents/service.py`
- Create: `backend/app/agents/router.py`
- Create: `backend/tests/agents/test_agent_api.py`
- Modify: `backend/app/main.py`

- [ ] Write tests for Agent CRUD, main-Agent delete rejection, model existence, globally enabled tool bindings, enabled Skill bindings, unique names, default work directory creation, custom directory resolution, prompt read/write, and binding summaries.
- [ ] Run Agent tests; expect failures.
- [ ] Implement resource schemas and validation in the service layer so cross-domain constraints never live in route functions.
- [ ] Store Agent metadata in `agents.json`, prompt content in `workspace/agents/<id>/agent.md`, and default runtime files in `workspace/runtime/<id>`.
- [ ] Register `/api/agents`, `/api/agents/{id}/prompt`, and binding-aware list/detail routes.
- [ ] Run Agent tests and backend suite; expect pass.
- [ ] Commit with `git commit -m "feat: configure local agents"`.

### Task 6: Scaffold the Vue application and design system

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/styles/main.css`
- Create: `frontend/src/components/layout/AppSidebar.vue`
- Create: `frontend/src/components/layout/AppHeader.vue`
- Create: `frontend/src/components/ui/*`
- Create: `frontend/src/views/DashboardView.vue`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/components/layout/AppSidebar.test.ts`

- [ ] Add a failing component test for Chinese navigation labels, active route styling, mobile drawer behavior, and accessible icon tooltips.
- [ ] Run `cd frontend && npm test -- --run`; expect initial failure.
- [ ] Configure Vue, Vite, Pinia, Router, Tailwind, Lucide, Vitest, and Playwright scripts.
- [ ] Define paper-workspace color tokens, type scale, compact controls, stable dimensions, focus states, reduced motion, and responsive layout in `main.css`.
- [ ] Build the fixed dark sidebar, mobile header/drawer, toast host, confirmation dialog, form controls, switch, tabs, empty state, status badge, table shell, and skeleton primitives.
- [ ] Build a functional dashboard from API summaries rather than static marketing content.
- [ ] Run frontend tests and `npm run build`; expect pass.
- [ ] Commit with `git commit -m "feat: scaffold management interface"`.

### Task 7: Build model, tool, and Skill management screens

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/models.ts`
- Create: `frontend/src/api/tools.ts`
- Create: `frontend/src/api/skills.ts`
- Create: `frontend/src/stores/models.ts`
- Create: `frontend/src/stores/tools.ts`
- Create: `frontend/src/stores/skills.ts`
- Create: `frontend/src/views/models/ModelsView.vue`
- Create: `frontend/src/views/models/ModelFormView.vue`
- Create: `frontend/src/views/tools/ToolsView.vue`
- Create: `frontend/src/views/skills/SkillsView.vue`
- Create: `frontend/src/views/skills/SkillFormView.vue`
- Create: `frontend/src/views/skills/SkillDetailView.vue`
- Create: `frontend/src/components/skills/SkillTree.vue`
- Create: `frontend/src/views/management.test.ts`
- Modify: `frontend/src/router/index.ts`

- [ ] Write failing tests for masked model secrets, connectivity state, immutable tool registry, Skill upload validation, toggles, directory expansion, and create/edit error states.
- [ ] Run the focused tests; expect failures.
- [ ] Implement typed API clients and Pinia stores with loading/error state and mutation refresh behavior.
- [ ] Build compact list/table screens, slide-over or routed forms, provider presets, secret preservation copy, test feedback, switches, ZIP drop zone, and accessible directory tree.
- [ ] Ensure every visible string is Simplified Chinese except provider/model/file identifiers.
- [ ] Run frontend tests and production build; expect pass.
- [ ] Commit with `git commit -m "feat: build resource management screens"`.

### Task 8: Build Agent management screens and management E2E coverage

**Files:**
- Create: `frontend/src/api/agents.ts`
- Create: `frontend/src/stores/agents.ts`
- Create: `frontend/src/views/agents/AgentsView.vue`
- Create: `frontend/src/views/agents/AgentEditorView.vue`
- Create: `frontend/src/components/agents/AgentBasicForm.vue`
- Create: `frontend/src/components/agents/PromptEditor.vue`
- Create: `frontend/src/components/agents/ToolSelector.vue`
- Create: `frontend/src/components/agents/SkillSelector.vue`
- Create: `frontend/src/views/agents/AgentEditorView.test.ts`
- Create: `frontend/e2e/management.spec.ts`
- Modify: `frontend/src/router/index.ts`

- [ ] Write failing tests for four editor tabs, dirty prompt state, bindings, undeletable main Agent, work-directory validation, and successful saves.
- [ ] Build typed API/store layers and a compact Agent table with direct run/edit actions.
- [ ] Build the four-column editor as top-level tabs with URL-preserved active tab, unsaved-change guards, searchable Skill selection, and tool permission explanations.
- [ ] Add Playwright management flows using a temporary backend workspace: model creation, Skill ZIP import, Agent creation, binding, prompt save, and reload persistence.
- [ ] Run backend tests, frontend tests, build, and management Playwright tests; expect pass.
- [ ] Commit with `git commit -m "feat: complete agent management"`.

