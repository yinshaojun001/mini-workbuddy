# Mini-workbuddy Design Specification

## 1. Goal

Build a lightweight, local-first Agent platform with a Vue management interface and a FastAPI runtime. The product manages model providers, built-in tools, imported Skills, configurable Agents, conversations, tool approvals, and execution history without an external database.

All user-facing interface copy is Simplified Chinese.

## 2. Scope

The first release includes:

- Model CRUD and connectivity tests for DeepSeek and Alibaba Cloud Bailian Qwen.
- Three fixed built-in tools: read file, write file, and execute command.
- Skill CRUD, enable/disable, directory inspection, and ZIP import.
- Agent CRUD, an undeletable built-in main Agent, model/tool/Skill bindings, editable `agent.md`, and an isolated work directory per Agent.
- Multi-turn conversations, streaming responses, OpenAI-compatible tool calling, Skill prompt injection, per-call approval for file writes and command execution, and run history.
- Local JSON, JSONL, Markdown, and directory-based persistence.

The release does not include authentication, remote multi-user access, database storage, distributed workers, MCP servers, memory/vector databases, multi-Agent orchestration, scheduled tasks, or arbitrary custom tool creation.

## 3. Architecture

Use a modular monolith. One FastAPI process owns REST APIs, SSE streams, repositories, model adapters, execution policy, and the Agent loop. The Vue single-page application consumes the API through domain-specific clients and stores only transient UI state in the browser.

Backend domains:

- `models`: provider configuration, secret handling, and connectivity diagnostics.
- `tools`: fixed tool registry, enable state, schemas, and executors.
- `skills`: metadata, safe ZIP extraction, Markdown content, and directory trees.
- `agents`: configuration, bindings, prompt files, and work directory policy.
- `sessions`: conversations, messages, and session metadata.
- `runtime`: prompt assembly, model adapters, tool loop, approval broker, and SSE events.
- `runs`: append-only audit records for model, tool, approval, and error events.

Repository interfaces isolate file persistence so a database can replace the storage implementation later without changing API handlers or runtime services.

## 4. Frontend Information Architecture

The application uses a fixed dark sidebar and a light, paper-like work area. The visual direction is "paper workspace": near-black navigation, cool off-white content, yellow-green primary accents, brick-red destructive actions, and amber approval states. Layouts are compact and operational rather than marketing-oriented.

Sidebar routes:

- `工作台`: model availability, Agent counts, active sessions, pending approvals, and recent activity.
- `智能体`: Agent list, create/edit operations, and run entry points.
- `模型`: DeepSeek and Qwen configurations and connectivity tests.
- `技能`: Skill list, enable state, editing, import, and directory details.
- `工具`: the three built-in tools and global enable switches.
- `运行记录`: conversations, tool traces, approvals, and failures.

Agent editing has four top-level sections:

1. `基本信息`: name, description, model, and isolated work directory.
2. `系统提示词`: online Markdown editing for the Agent's `agent.md`, with dirty state and save feedback.
3. `工具选择`: checkboxes for the three globally available tools and their permission behavior.
4. `技能选择`: searchable imported Skills with enabled state and `SKILL.md` summaries.

The run page uses a session list, a central conversation timeline, and a runtime context panel. On narrow screens, the two supporting panels become drawers. Approval requests appear inline in the conversation with exact path/command parameters and `允许一次` and `拒绝` actions.

## 5. Local Storage

```text
workspace/
├── models.json
├── tools.json
├── agents.json
├── skills/
│   └── <skill-id>/
│       ├── metadata.json
│       ├── SKILL.md
│       └── <skill-owned files and directories>
├── agents/
│   └── <agent-id>/
│       └── agent.md
├── sessions/
│   └── <session-id>/
│       ├── session.json
│       └── messages.jsonl
├── runs/
│   └── <run-id>.jsonl
└── runtime/
    └── <agent-id>/
```

JSON collection updates use a temporary file followed by atomic replacement. JSONL files are append-only. IDs are generated UUID strings. Timestamps are ISO 8601 UTC values returned to the frontend for localized display.

The initial seed creates DeepSeek and Qwen provider templates without API keys, the three enabled built-in tools, and an enabled main Agent. The main Agent cannot be deleted but can otherwise be edited.

## 6. Model Configuration

Each model contains an ID, display name, provider, model identifier, base URL, API key, enabled state, and optional generation settings. Provider defaults are:

- DeepSeek: `https://api.deepseek.com`, default model `deepseek-chat`.
- Alibaba Cloud Bailian: `https://dashscope.aliyuncs.com/compatible-mode/v1`, default model `qwen-plus`.

Both adapters use OpenAI-compatible chat completion and tool-calling payloads. API responses never return the stored secret. They return `has_api_key` and a masked hint. An empty API key on update preserves the existing key.

Connectivity testing sends a minimal non-streaming request with low output limits. It distinguishes invalid configuration, authentication failure, rate limiting, timeout, network failure, and incompatible response errors.

## 7. Skills

A valid Skill is a directory containing `SKILL.md`. Metadata stores ID, name, description, enabled state, and update time. Editing supports metadata and `SKILL.md`; additional files are read-only in the first release.

ZIP import accepts either `SKILL.md` at archive root or one containing top-level directory. The importer rejects ambiguous archives containing multiple candidate Skill roots. It also rejects absolute paths, `..` traversal, symbolic links, oversized archives, excessive expanded size, and duplicate IDs. Import writes to a temporary directory, validates the complete result, and atomically moves it into `workspace/skills`.

The details API returns a structured directory tree and serves text file previews only for files inside the Skill directory. Binary files are listed but not previewed.

## 8. Agent Runtime

For each user message, the runtime:

1. Loads the Agent, selected model, globally enabled and Agent-bound tools, enabled selected Skills, prompt file, and recent conversation messages.
2. Uses `agent.md` as the system prompt and appends a clearly delimited Skill section containing each selected Skill's name, description, and `SKILL.md` content.
3. Calls the selected provider using a streaming OpenAI-compatible request.
4. Emits text deltas and runtime status through SSE.
5. Validates every model-requested tool against the global registry and Agent bindings.
6. Executes read-file calls immediately within the Agent work directory.
7. Creates a pending approval for write-file and command calls, emits it through SSE, and pauses that run until the user allows or rejects the call.
8. On approval, executes the call once and returns a tool result to the model. On rejection, returns a structured rejection result to the model.
9. Repeats until the model produces a final answer, the configured tool-round limit is reached, the request is cancelled, or an error occurs.
10. Persists messages and all model/tool/approval/error events.

The default maximum is eight model/tool rounds per user message. A cancelled or disconnected browser does not implicitly approve work. Pending approvals remain pending and can be resolved after reconnection while the backend process remains alive. A backend restart marks in-progress runs as interrupted; it does not automatically resume model execution.

## 9. Tool Security

Every Agent owns an isolated work directory. The default is `workspace/runtime/<agent-id>`. A custom directory is allowed only when it exists or can be created by the application and is stored as a resolved absolute path.

Read and write targets are resolved before access and must remain descendants of the Agent work directory. Symlink targets that escape the work directory are rejected. File reads have size limits and return a clear error for binary content.

Command execution:

- Requires approval for every call.
- Runs with the Agent work directory as `cwd`.
- Uses an argument array when the model supplies one; string commands are executed through the platform shell only after approval and are labeled as shell commands in the UI.
- Has a configurable timeout and captured output limits.
- Does not inherit application secrets such as model API keys in its environment.
- Records command, directory, duration, exit code, truncated stdout, and truncated stderr.

Tool approval means `allow once`; there is no persistent allow rule in this release.

## 10. API and Streaming Contract

REST resources use `/api`:

- `/api/models`
- `/api/tools`
- `/api/skills`
- `/api/agents`
- `/api/sessions`
- `/api/runs`
- `/api/approvals`

CRUD uses standard GET, POST, PUT, PATCH, and DELETE semantics. ZIP import uses multipart upload. Markdown edits use JSON bodies with explicit content fields.

Starting a run creates a run resource and opens an SSE response. Event types include `run.started`, `message.delta`, `message.completed`, `tool.requested`, `approval.required`, `tool.started`, `tool.completed`, `run.completed`, `run.interrupted`, and `run.failed`. Every event carries a run ID, sequence number, timestamp, and event-specific data so the frontend can deduplicate and order events.

Errors use:

```json
{
  "error": {
    "code": "MODEL_AUTH_FAILED",
    "message": "模型鉴权失败",
    "details": {}
  }
}
```

## 11. UX and Error Handling

Forms use field-level validation. Mutations show concise success or failure toasts. Destructive actions require confirmation. Empty states always expose the relevant create/import action. Loading states preserve element dimensions to avoid layout shifts.

Provider errors include a retry action and configuration link. Runtime errors stay in the conversation timeline and are also written to the run log. Approval cards become immutable result summaries after resolution. Secret fields explain whether a key is already stored without revealing it.

## 12. Testing and Acceptance

Backend tests cover repositories, atomic writes, ID rules, path containment, symlink escape, ZIP validation, CRUD APIs, provider error mapping, prompt assembly, tool authorization, approval allow/reject, round limits, interruption, and SSE event ordering.

Model adapter and Agent-loop tests use deterministic fake OpenAI-compatible responses. Tests never require a real provider key.

Frontend tests cover API clients, domain stores, forms, secret preservation, Skill tree rendering, Agent bindings, SSE reduction, and approval interaction. Playwright covers:

1. Create and test a model with a mocked backend provider.
2. Import and inspect a Skill ZIP.
3. Configure an Agent with model, tools, Skills, prompt, and work directory.
4. Run a conversation that reads a file, requests a write approval, receives approval, and completes.
5. Reject a command approval and verify the rejection appears in the timeline and run log.

Final verification includes backend and frontend test suites, production frontend build, desktop and mobile Playwright screenshots, overflow checks, and inspection that no interface text remains in English except provider/model names, file names, command content, and technical identifiers.

## 13. Delivery Phases

Phase 1 delivers the project skeleton, storage repositories, model/tool/Skill/Agent APIs, and all management screens. It is independently runnable and testable.

Phase 2 delivers sessions, model adapters, the Agent loop, tool execution, approvals, run history, and the run interface. It builds on the Phase 1 contracts without changing their resource shapes.
