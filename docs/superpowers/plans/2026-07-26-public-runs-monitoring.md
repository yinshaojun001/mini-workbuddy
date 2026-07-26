# 公开运行监控实施计划

规格来源：`docs/superpowers/specs/2026-07-26-public-runs-monitoring-design.md`

## 1. 当前状态与执行原则

当前公开 Fortune 请求已经通过 `AgentEngine`、绑定 Agent、Skill 和 DeepSeek 模型执行，并将匿名内容写入 `workspace/public_sessions/{session_id}/`。缺口集中在三个边界：运行事件没有落盘、生命周期没有永久累计指标、管理端没有公开会话 API 和页面。

实施遵循以下规则：

- 保持公开运行与普通 `sessions/runs` 存储和 API 完全隔离。
- 每个阶段先补失败测试，再实现最小行为，最后运行相关回归测试。
- 事件文件只保存白名单字段；消息只保存在 `messages.json`。
- 永久指标只保存累计数字，不从历史会话反推。
- 不改变 Fortune 公网 Nginx 白名单；管理 API 只通过 Workbuddy 域名访问。
- 不覆盖或迁移管理员现有模型配置、API Key 和工作区数据。
- 每个阶段形成独立提交，便于 PR 审阅和必要时回退。

## 2. 依赖路线

```text
事件/指标存储原语
        |
        v
公开运行生命周期接入 -----> 删除与 TTL 计数
        |
        v
管理 API 与隐私模型
        |
        v
管理前端与自动刷新
        |
        v
全量回归、浏览器验收、PR 更新
```

关键路径是后端存储契约 -> 生命周期接入 -> API 响应契约 -> 前端。前端不与尚未验证的临时 API 并行开发。

## 3. 阶段一：事件与累计指标存储

### 目标

交付两个边界清晰的仓库：一个只管理 TTL 内的安全运行事件，一个只管理永久累计数字。

### 任务 1.1：公开运行事件仓库

新增：

- `backend/app/public_runtime/events.py`
- `backend/tests/test_public_run_events.py`

实现：

- `PublicRunEventRepository` 以公开会话根目录为入口。
- `append(session_id, run_id, event)` 写入 `runs/{run_id}.jsonl`。
- 使用类级 `RLock` 保护同一进程内的逐行追加。
- 写入前只接受明确字段：`run_id`、`sequence`、`timestamp`、`type`、`mode`、`duration_ms`、`model_id`、`error_code`。
- `events(session_id)` 读取全部 run 文件，忽略损坏行，按时间、run ID、sequence 稳定排序。
- 有消息但没有事件文件的历史会话返回 `historical_events_unavailable=true`。
- 以最后事件是否为 `run.completed` 或 `run.failed` 推导 `completed`、`failed` 或 `interrupted`。

测试先证明：

- 事件写入正确的会话目录。
- 并发追加不丢行，sequence 顺序可恢复。
- 任意额外字段和包含消息正文的 payload 都不会落盘。
- 损坏 JSON 行不阻断整个详情读取。
- 空 runs 目录被识别为历史未采集，而不是空的成功运行。

验证：

```bash
cd backend
uv run pytest tests/test_public_run_events.py -q
```

### 任务 1.2：永久指标仓库

新增：

- `backend/app/public_runtime/metrics.py`
- `backend/tests/test_public_metrics.py`

实现：

- `PublicMetricsRepository` 使用 `AtomicJsonStore(workspace/public_metrics.json)`。
- 类级 `RLock` 包住完整的 read-modify-write，避免多个仓库实例丢失增量。
- 提供语义方法：`session_created`、`run_started`、`run_completed`、`run_failed` 和 `session_deleted`。
- `run_completed` 根据 `report/question` 更新对应成功计数、`runs_completed` 和 `total_duration_ms`。
- `run_failed` 根据模式更新失败计数，并只接受归一化安全错误码。
- `session_deleted` 只接受 `admin`、`visitor`、`ttl` 三种原因。
- 读取时计算每个应用和全局的平均耗时，不持久化平均值或全局重复副本。

测试先证明：

- 新文件从 version 1 空结构开始。
- 每种生命周期方法只修改规定计数。
- 多线程、多仓库实例更新不丢计数。
- 平均耗时使用成功运行数作为分母，零运行返回 0。
- 指标 JSON 递归检查不包含 session ID、消息、出生资料、owner、Cookie、IP 或 IP hash。
- 无效模式、错误码或删除原因被拒绝，不能形成任意动态字段。

验证：

```bash
cd backend
uv run pytest tests/test_public_metrics.py -q
```

阶段提交：

```text
feat: add public run event and metrics stores
```

阶段完成条件：两个仓库可以独立使用，存储隐私测试和并发测试全部通过。

## 4. 阶段二：接入公开运行生命周期

### 目标

在不改变 Fortune SSE 公共契约和 `tools=[]` 安全边界的前提下，为新会话、报告、追问、失败和清理写入事件及指标。

### 任务 2.1：建立仓库依赖和错误归一化

修改：

- `backend/app/public_runtime/service.py`
- `backend/tests/test_public_runtime_api.py`
- `backend/tests/test_public_runtime_safety.py`

实现：

- 将当前 `repositories(settings)` 扩展为具名依赖容器或拆分为小型仓库工厂，避免 tuple 位置不断增长。
- 创建会话成功后调用 `metrics.session_created(app_id)`；排盘、配额预留或目录创建失败时不得计数。
- 增加内部错误归一化函数，把现有模型错误映射到安全集合：`MODEL_TIMEOUT`、`MODEL_AUTH_FAILED`、`MODEL_RATE_LIMITED`、`MODEL_RESPONSE_INVALID`、`ENGINE_FAILED`。
- 保持客户端现有中文安全错误信息；原始异常文本不得进入事件。

### 任务 2.2：持久化运行事件和运行指标

修改：

- `backend/app/public_runtime/service.py`
- `backend/tests/test_public_runtime_api.py`
- `backend/tests/test_public_runtime_safety.py`

实现：

- 请求通过 `owned_session`、`claim_run` 和模型上下文校验后生成 `run_id`，记录 `runs_started`。
- 用单一内部 `record_event` 函数同时管理 sequence、时间戳和白名单事件写入。
- 正常序列为 `run.started`、`agent.started`、`model.started`、`model.completed`、`agent.completed`、`run.completed`。
- 失败路径以准确的 `model.failed`、`agent.failed` 或 `run.failed` 结束，终止事件只带安全错误码和耗时。
- `duration_ms` 使用单调时钟计算；仅成功终止时计入累计成功耗时。
- SSE 继续只发送现有公开事件子集，不把管理诊断事件或 `model_id` 暴露给 Fortune 访客。
- 报告和追问消息保存、quota commit/release、question_count 更新保持现有语义。
- `asyncio.CancelledError` 保留已写事件，不增加成功/失败累计数；详情将该 run 推导为 `interrupted`。

测试先证明：

- 报告成功和追问成功各产生完整事件序列及正确指标。
- 模型超时、鉴权、限流、无效响应和未知异常得到安全错误码。
- 执行前的过期、额度和状态拒绝不创建 run，不增加失败数。
- SSE 响应不新增管理事件或敏感字段，工具列表仍严格为空。
- 取消流后只有部分事件，消息不保存，quota 行为不回归。
- 事件 JSONL 不包含提示词、出生资料、用户问题、模型回答或 API Key。

验证：

```bash
cd backend
uv run pytest tests/test_public_runtime_api.py tests/test_public_runtime_safety.py tests/test_public_run_events.py tests/test_public_metrics.py -q
```

### 任务 2.3：统一访客删除和 TTL 清理计数

修改：

- `backend/app/public_runtime/router.py`
- `backend/app/public_runtime/cleanup.py`
- `backend/app/main.py`
- `backend/tests/test_public_sessions.py`
- `backend/tests/test_public_runtime_api.py`

实现：

- 访客删除实际移除目录后记录 `visitor_deletions`。
- TTL 清理实际移除目录后记录 `ttl_cleanups`。
- 启动清理和 15 分钟循环共享同一个 metrics 实例/路径。
- 现有运行中断恢复行为保留；只有真正过期且成功删除才增加 TTL 计数。
- 重复删除、目录已不存在和竞争失败不增加任何删除计数。

验证：

```bash
cd backend
uv run pytest tests/test_public_sessions.py tests/test_public_runtime_api.py -q
```

阶段提交：

```text
feat: capture public runtime telemetry
```

阶段完成条件：真实公开报告和追问可同时产生原有 SSE、TTL 事件和永久累计数字，公开行为测试无回归。

## 5. 阶段三：管理 API 与隐私响应模型

### 目标

提供独立、可筛选、默认脱敏的 `/api/public-runs` 管理接口，并实现管理员删除。

### 任务 3.1：会话摘要、详情和状态映射

修改：

- `backend/app/public_runtime/repository.py`

新增：

- `backend/app/public_runtime/admin_service.py`
- `backend/tests/test_public_runs_admin_api.py`

实现：

- repository 提供在锁内删除和读取会话文件集合的原语，不直接构造 HTTP 响应。
- admin service 将内部状态映射为 `active/running/completed/failed/expired`。
- `active` 包含可继续交互的 `chart_ready`、`report_ready` 和 `interrupted`；`running` 包含 `report_running/question_running`；问题额度耗尽且报告存在时为 `completed`。
- 摘要计算消息数、run 数、最近 run 状态，并按 `updated_at` 倒序。
- 详情组合 session、birth input、chart、messages 和安全 events。
- 默认 birth response 对姓名、日期、时间等字段做明确遮罩；`include_sensitive=true` 才读取完整业务字段。
- 所有响应都由白名单字段重新构造，禁止直接返回 session/input/chart 原对象。

### 任务 3.2：列表、统计和详情路由

新增：

- `backend/app/public_runtime/admin_router.py`

修改：

- `backend/app/main.py`
- `backend/tests/test_public_runs_admin_api.py`

实现：

- `GET /api/public-runs` 支持 `app_id`、status、session ID query、limit 和 opaque cursor。
- cursor 编码排序锚点，不包含 birth、owner 或 IP 数据；非法和过期 cursor 返回 `422 VALIDATION_ERROR`。
- `GET /api/public-runs/stats` 返回 per-app 和读取时派生的 all-app totals。
- `GET /api/public-runs/{session_id}` 默认脱敏；`include_sensitive=true` 显式返回完整出生业务字段。
- 路由声明顺序保证 `/stats` 不被 `{session_id}` 捕获。
- 继续使用 Workbuddy 域名现有 Nginx Basic Auth；应用本身不引入第二套账号系统。

测试先证明：

- 列表排序、所有过滤、搜索、limit 和跨页 cursor 稳定。
- 默认详情响应中不存在原始姓名、完整生日和时间。
- sensitive 详情只增加允许的出生业务字段。
- 任何响应递归检查都没有 `owner_hash`、`ip_hash`、reservation、Cookie、prompt 或 API Key。
- 过期未清理会话显示 `expired`；已清理会话返回 404。
- 历史会话详情返回对话和 `historical_events_unavailable`。

### 任务 3.3：管理员删除

修改：

- `backend/app/public_runtime/repository.py`
- `backend/app/public_runtime/admin_service.py`
- `backend/app/public_runtime/admin_router.py`
- `backend/tests/test_public_runs_admin_api.py`
- `backend/tests/test_public_quota.py`

实现：

- 在会话级/仓库锁内检查状态并删除整个目录。
- `report_running/question_running` 返回 `409 SESSION_RUNNING`。
- 成功删除返回 204，并在删除完成后增加 `admin_deletions`。
- 已提交 quota 不回退；存在未提交 reservation 时调用现有 `quota.release`。
- 不存在、重复删除、与访客或 TTL 清理竞争失败返回 404 且不计数。

验证：

```bash
cd backend
uv run pytest tests/test_public_runs_admin_api.py tests/test_public_sessions.py tests/test_public_quota.py -q
uv run pytest -q
```

阶段提交：

```text
feat: add public runs management API
```

阶段完成条件：全部管理端响应符合白名单和脱敏契约，删除与计数在竞争路径上保持一致。

## 6. 阶段四：Workbuddy 公开运行页面

### 目标

按批准的「运营总览 + 会话表格 + 右侧详情抽屉」设计交付完整管理体验。

### 任务 4.1：前端契约和可识别 API 错误

修改：

- `frontend/src/api/client.ts`
- `frontend/src/types.ts`

新增：

- `frontend/src/api/client.test.ts`

实现：

- 增加 `ApiRequestError`，保留服务端 status、code、message 和 details，兼容所有现有 `(reason as Error).message` 用法。
- 定义 `PublicRunSummary`、`PublicRunDetail`、`PublicRunEvent`、`PublicRunStats` 和分页 envelope 类型。
- 为列表 query 使用 `URLSearchParams`，不手写字符串拼接和转义。

测试先证明：

- 204、正常 JSON、结构化错误和非 JSON 错误行为不回归。
- `SESSION_RUNNING` 与 404 可由页面稳定识别。

### 任务 4.2：路由、导航和页面数据流

修改：

- `frontend/src/router/index.ts`
- `frontend/src/components/layout/AppSidebar.vue`

新增：

- `frontend/src/views/PublicRunsView.vue`
- `frontend/src/views/PublicRunsView.test.ts`

实现：

- 增加 `/public-runs` 宽屏路由和「公开运行」导航项，使用 Lucide `RadioTower` 或语义最接近的现有图标。
- 首次并行加载 stats 和 session list；筛选变化重置 cursor 并重新加载。
- 每 15 秒刷新当前列表；抽屉打开时同时刷新该 session 详情。
- 使用请求序号或 `AbortController` 防止较慢的旧响应覆盖较新的筛选/会话。
- 自动刷新失败保留旧内容并显示非阻塞状态；手动刷新显示明确错误。
- 组件卸载时清理 interval 和进行中的请求。

### 任务 4.3：运营总览、表格和详情抽屉

修改：

- `frontend/src/views/PublicRunsView.vue`
- `frontend/src/styles/main.css`
- `frontend/src/views/PublicRunsView.test.ts`

实现：

- 四个稳定尺寸统计格展示累计会话、成功运行、失败运行和平均耗时。
- 提供 app/status 下拉筛选、session ID 搜索、手动刷新和游标翻页。
- 紧凑表格展示 session、app、状态、消息数、run 数、剩余问题、最近活动和过期时间。
- 行点击打开右侧 drawer；遮罩、关闭按钮和 Escape 均可关闭。
- drawer 默认打开「对话」，第二 tab 为「运行事件」。
- 出生资料默认使用接口的 masked 值；点击「显示敏感资料」后单独请求 sensitive 详情。
- 关闭或切换 session 时销毁 sensitive detail；不得缓存到列表或全局状态。
- 事件按 run 分组，展示阶段、耗时、安全错误码和 interrupted/历史未采集状态。
- 删除使用二次确认，文案明确不可恢复且不返还已消耗额度；204 后关闭 drawer 并刷新 stats/list。
- 409 保持 drawer 打开并提示等待运行结束；404 关闭 drawer 并刷新列表。
- 使用现有 CSS 变量、6px radius、表格和 badge 模式；不重做其他管理页面。

测试先证明：

- 初始渲染、筛选、搜索、翻页和手动刷新发出正确请求。
- fake timer 下 15 秒刷新，unmount 后不再请求。
- 自动刷新失败保留表格和选中项。
- 默认脱敏、显式 reveal、关闭/切换后重新脱敏。
- 对话/事件 tabs、historical/interrupted/error 显示正确。
- 删除确认、成功、409 和 404 状态转换正确。
- loading、empty 和 error 状态可访问且布局稳定。

验证：

```bash
cd frontend
npm test -- --run src/api/client.test.ts src/views/PublicRunsView.test.ts
npm test -- --run
npm run build
```

阶段提交：

```text
feat: add public runs monitoring UI
```

阶段完成条件：管理员可从导航完成筛选、查看、揭示敏感资料和删除的完整工作流，自动刷新无资源泄漏。

## 7. 阶段五：隐私、集成与浏览器验收

### 目标

用真实本地链路验证功能、响应隐私、响应式布局和生产网络边界，并更新现有 PR。

### 任务 5.1：跨生命周期隐私回归

新增：

- `backend/tests/test_public_monitoring_privacy.py`

必要时修改：

- `backend/tests/test_public_runtime_safety.py`
- `backend/tests/test_public_runs_admin_api.py`

建立一条包含可识别 sentinel 值的真实测试会话，执行报告和追问，然后递归检查：

- 默认管理详情只在 `messages` 中包含对话正文，events 和 metrics 不得包含正文。
- 完整生日和时间只在 `include_sensitive=true` 的允许字段出现。
- owner hash、IP hash、Cookie、reservation ID、API Key 和系统 prompt 不出现在任何管理响应、事件或 metrics。
- 删除后会话目录完全消失，永久 metrics 只留下数字。

### 任务 5.2：本地完整链路与浏览器检查

运行：

```bash
cd backend && uv run pytest -q
cd frontend && npm test -- --run && npm run build
cd fortune-engine && npm test && npm run build
cd fortune-frontend && npm test -- --run && npm run build && npm run test:e2e
```

启动本地 backend、frontend、fortune-engine 和 fortune-frontend。使用真实 Fortune 页面生成一份报告并至少追问一次，然后在 Workbuddy `/public-runs` 验证：

- desktop 1440x900 和 mobile 390x844 截图。
- 表格、drawer、长 session ID、长消息和错误码无溢出或重叠。
- drawer 打开/关闭、tab、敏感揭示和删除操作可用。
- 15 秒刷新不重置选择、tab 或滚动位置。
- 浏览器网络面板的默认 detail 响应无敏感出生字段。
- frontend 控制台无错误，页面无未处理请求。

### 任务 5.3：生产边界与 PR 更新

只做配置验证，不扩大 Nginx 代理范围：

- `deploy/fortune-nginx.conf` 仍仅代理 `/api/public/apps/fortune` 及其子路径。
- Fortune 域名 `/api/public-runs` 返回 404。
- Workbuddy 域名继续由现有 Basic Auth 保护所有 `/api/` 和前端路由。
- `.github/workflows/deploy.yml` 的现有全量测试和构建步骤覆盖本次修改，无需新增部署通道。

最终检查：

```bash
git diff --check
git status --short
git log --oneline --decorate -8
```

将阶段提交 push 到现有 `feat/fortune-published-app` 和 PR #1。用户仍负责最终 merge；GitHub Actions 只会在合并进入 `main` 后自动部署。

最终完成条件：

- 后端、管理前端、Fortune 前端和排盘引擎全部测试/构建通过。
- 真实公开运行能在管理端看到对话和事件。
- 默认响应及永久存储满足隐私白名单。
- 管理删除与配额、TTL、累计指标保持一致。
- desktop/mobile 浏览器验收通过。
- 现有 PR 包含全部提交，生产部署仍等待用户 merge。

## 8. 阶段提交清单

```text
feat: add public run event and metrics stores
feat: capture public runtime telemetry
feat: add public runs management API
feat: add public runs monitoring UI
test: verify public monitoring privacy and integration
```

测试阶段如发现实现必须偏离规格，应先更新规格和计划并说明原因，不以临时代码绕过已批准的隐私、TTL、删除或网络边界。
