# 知命公开 Agent 应用实施计划

规格来源：`docs/superpowers/specs/2026-07-24-fortune-published-app-design.md`

## 1. 执行原则

- 依赖顺序固定为：确定性排盘引擎 -> 发布层后端 -> 管理前端 -> 公开前端 -> 部署上线。
- 每个阶段先写失败测试，再实现最小代码使测试通过。
- 每个阶段独立提交；下一阶段不得依赖未验证的隐式行为。
- 公开运行永远强制 `tools=[]`，不复用管理会话所有权模型。
- 不修改或删除现有 `workspace/` 数据，不覆盖管理员已配置的模型密钥。
- 线上变更必须先健康检查，再切换 Nginx/前端链接；失败恢复上一版。

## 2. 阶段一：确定性排盘服务

### 目标

交付一个无状态、无公网端口、可独立测试的 Node 服务，把 OpenFate 输出规范化为稳定的内部 HTTP 契约。

### 任务 1.1：建立服务骨架与锁定依赖

新增：

- `fortune-engine/package.json`
- `fortune-engine/package-lock.json`
- `fortune-engine/tsconfig.json`
- `fortune-engine/src/server.ts`
- `fortune-engine/src/chart.ts`
- `fortune-engine/src/schema.ts`
- `fortune-engine/tests/chart.test.ts`
- `fortune-engine/Dockerfile`

要求：

- Node 22。
- 精确锁定 `@openfate/bazi-engine@1.1.1` 和 `@openfate/true-solar-time@4.0.2`。
- 使用 Node 内置 `http`，不引入 Web 框架。
- `GET /health` 返回 `{ "status": "ok" }`。
- `POST /chart` 限制 JSON 大小，拒绝未知字段和非法组合。
- 日志只记录请求 ID、耗时和结果，不记录出生资料正文。

验证：

```bash
cd fortune-engine
npm ci
npm test
npm run build
```

### 任务 1.2：城市目录生成

新增：

- `fortune-engine/scripts/build-city-catalog.mjs`
- `fortune-engine/data/cities.json`
- `fortune-engine/data/ATTRIBUTION.md`
- `fortune-engine/tests/city-catalog.test.ts`

要求：

- 生成物只含中国大陆省级/地级城市、稳定代码、父级代码、名称和中心点经度。
- 记录 GeoNames 数据日期、来源 URL、CC BY 署名和输入校验值。
- 构建不在生产启动时联网；运行时只读版本化 JSON。
- 测试北京、乌鲁木齐、上海、广州等代表性经度和父子关系。

### 任务 1.3：排盘契约和 golden cases

测试覆盖：

- 北京时间普通四柱。
- 真太阳时关闭/开启。
- 经度修正跨时辰。
- 23:00 子时换日。
- 节气交界。
- 时辰不详。
- 男女大运顺逆。
- 日期边界和错误响应。

服务返回项目稳定 envelope，不直接透传包内部所有字段：

```json
{
  "chart": {},
  "policy": {},
  "attribution": {}
}
```

阶段提交：

```text
feat: add deterministic bazi engine service
```

阶段完成条件：服务测试全绿，Docker 镜像可构建，golden diff 无未审阅变化。

## 3. 阶段二：Published App 与公开运行后端

### 目标

增加管理应用域、公开匿名会话、配额、TTL、排盘编排和无工具 Agent 流式运行。

### 任务 2.1：配置和应用管理域

修改：

- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/storage/bootstrap.py`

新增：

- `backend/app/apps/__init__.py`
- `backend/app/apps/router.py`
- `backend/app/apps/repository.py`
- `backend/tests/test_apps_api.py`

设置：

- `PUBLIC_SESSION_SECRET`
- `PUBLIC_IP_HASH_SECRET`
- `BAZI_ENGINE_URL`
- `FORTUNE_ORIGIN`

实现 `/api/apps` CRUD、Slug 唯一性、Agent 存在性、限额范围和 TTL 范围验证。

### 任务 2.2：默认 Skill、Agent 和应用的幂等安装

新增：

- `backend/app/bootstrap/fortune.py`
- `backend/app/bootstrap/assets/bazi-interpreter/SKILL.md`
- `backend/app/bootstrap/assets/fortune-agent.md`
- `backend/tests/test_fortune_bootstrap.py`

规则：

- 缺失时创建 `bazi-interpreter`、`fortune-bazi-agent` 和 `fortune` 应用。
- 使用现有 DeepSeek 模板 ID。
- 已存在时不覆盖 Skill、Agent prompt、模型绑定或 API Key。
- 公开应用模型不可用时返回健康状态，不阻断整个 Workbuddy 启动。

### 任务 2.3：排盘客户端与稳定模型

新增：

- `backend/app/fortune/__init__.py`
- `backend/app/fortune/chart_client.py`
- `backend/app/fortune/models.py`
- `backend/app/fortune/cities.py`
- `backend/tests/test_fortune_chart_client.py`

要求：

- 使用现有 `httpx`，设置连接、读取和总超时。
- 校验排盘服务响应，映射为 `CHART_CALCULATION_FAILED`。
- 不把内部 URL、堆栈或原始异常返回公开客户端。

### 任务 2.4：匿名身份、配额和会话仓库

新增：

- `backend/app/public_runtime/__init__.py`
- `backend/app/public_runtime/identity.py`
- `backend/app/public_runtime/quota.py`
- `backend/app/public_runtime/rate_limit.py`
- `backend/app/public_runtime/repository.py`
- `backend/app/public_runtime/cleanup.py`
- `backend/tests/test_public_identity.py`
- `backend/tests/test_public_quota.py`
- `backend/tests/test_public_sessions.py`

要求：

- 签名随机 Cookie，访客和 IP 使用不同 HMAC 密钥。
- 原始 IP 不落盘。
- 每日计数原子写入并由异步锁串行化。
- 实现 `available/reserved/committed/released`。
- 实现 15 分钟预留超时、24 小时会话 TTL、启动和每 15 分钟清理。
- 所有权失败统一 404。

### 任务 2.5：公开 API 和流式运行

新增：

- `backend/app/public_runtime/router.py`
- `backend/app/public_runtime/service.py`
- `backend/app/public_runtime/prompt.py`
- `backend/tests/test_public_runtime_api.py`
- `backend/tests/test_public_runtime_safety.py`

必要时小范围提取：

- `backend/app/runtime/context.py`
- `backend/app/runtime/streaming.py`

要求：

- 实现规格中的 6 个公开接口。
- 创建会话强制先排盘。
- 初始报告和追问复用 `AgentEngine` 与 `OpenAICompatibleAdapter`。
- 公开上下文使用固定 Agent/Skill/命盘，强制工具列表为空。
- SSE 只返回公开事件子集。
- 断线/重启标记 interrupted，不保存不完整助手消息。
- Origin、请求体、问题长度、并发状态和最大追问在服务端校验。
- 高风险响应边界使用假模型测试。

阶段验证：

```bash
cd backend
uv run pytest
```

阶段提交：

```text
feat: add published app public runtime
```

## 4. 阶段三：Workbuddy 应用管理页面

### 目标

管理员可以查看、创建、编辑、启停和删除 Published App，并看到公开 URL、绑定 Agent 和健康状态。

修改：

- `frontend/src/router/index.ts`
- `frontend/src/components/layout/AppSidebar.vue`
- `frontend/src/types.ts`
- `frontend/src/api/client.ts`

新增：

- `frontend/src/views/AppsView.vue`
- `frontend/src/views/AppsView.test.ts`

页面能力：

- 紧凑表格列出名称、Slug、Agent、状态、额度、TTL 和公开 URL。
- 新建/编辑表单使用选择器、数字输入和开关。
- 禁用状态、模型不可用状态和复制 URL 命令。
- 删除前确认，不删除 Agent 和历史管理数据。
- 保持现有 Workbuddy 视觉系统，不重做无关页面。

验证：

```bash
cd frontend
npm test -- --run
npm run build
```

阶段提交：

```text
feat: add published app management UI
```

## 5. 阶段四：知命公开前端

### 目标

交付独立构建、不包含管理代码的公开 Vue 应用。

新增：

- `fortune-frontend/package.json`
- `fortune-frontend/package-lock.json`
- `fortune-frontend/vite.config.ts`
- `fortune-frontend/index.html`
- `fortune-frontend/src/main.ts`
- `fortune-frontend/src/App.vue`
- `fortune-frontend/src/api.ts`
- `fortune-frontend/src/types.ts`
- `fortune-frontend/src/sse.ts`
- `fortune-frontend/src/markdown.ts`
- `fortune-frontend/src/styles.css`
- `fortune-frontend/src/components/BirthForm.vue`
- `fortune-frontend/src/components/BaziChart.vue`
- `fortune-frontend/src/components/ReadingReport.vue`
- `fortune-frontend/src/components/QuestionComposer.vue`
- `fortune-frontend/src/components/PrivacyNotice.vue`
- 对应 Vitest 测试和 Playwright 配置/测试

状态机：

```text
loading -> form -> chart_ready -> report_streaming -> report_ready
                                      |                 |
                                      v                 v
                                    error         question_streaming
```

实现：

- 打开即表单，无营销 Hero。
- 公历、男/女、时间/时辰不详、省市、真太阳时、关注方向。
- 结构化四柱、计算口径、五行/十神/大运摘要。
- 固定报告章节和 Markdown 安全渲染。
- 同命盘追问和剩余问题数。
- 会话恢复、过期、额度耗尽、立即删除。
- OpenFate 和 GeoNames attribution。
- 文化娱乐、隐私和高风险领域声明。
- 使用有明确授权的位图资产；若外部资产授权不够清楚，生成原创位图并记录来源。

视觉验收：

- 320、390、768、1440 px。
- 不出现横向滚动、文字溢出、遮挡或动态布局跳动。
- Playwright 截图检查表单、报告、流式回复、错误、额度耗尽和移动端。
- 使用浏览器像素检查确认位图和主要内容非空。

验证：

```bash
cd fortune-frontend
npm test -- --run
npm run build
npm run test:e2e
```

阶段提交：

```text
feat: add public fortune experience
```

## 6. 阶段五：自动部署和上线

### 目标

扩展现有 GitHub Actions 和服务器脚本，安全部署双镜像与双前端，并上线 `fortune.inshocking.com`。

修改：

- `.dockerignore`
- `.github/workflows/deploy.yml`
- `backend/Dockerfile`
- `deploy/server-deploy.sh`
- `deploy/nginx.conf`
- `README.md`

新增：

- `deploy/fortune-nginx.conf`
- `deploy/fortune-engine-healthcheck.sh`（仅在 shell 逻辑复杂到值得独立文件时添加）

部署要求：

- GitHub runner 构建两个 amd64 镜像，服务器不构建。
- 上传 Workbuddy 和 Fortune 两套静态产物。
- 创建专用 Docker network。
- 排盘服务不发布宿主机端口。
- 注入三项新服务器密钥和内部 URL。
- 先检查排盘服务，再检查 FastAPI，再原子切换前端。
- 记录上一版镜像，失败时恢复容器和 `current` 链接。
- Nginx `fortune` 站点拒绝管理 API，设置 SSE 和安全响应头。
- 阿里云 DNS 添加 `fortune -> 47.93.35.251`。
- Certbot 签发并验证自动续期。

服务器验证：

```bash
curl -I http://fortune.inshocking.com/
curl -I https://fortune.inshocking.com/
curl https://fortune.inshocking.com/api/public/apps/fortune
docker stats --no-stream mini-workbuddy-backend fortune-bazi-engine
free -h
swapon --show
```

线上安全验收：

- `https://fortune.inshocking.com/api/models` 返回 404。
- 未知 Origin 公开请求返回 403。
- 不同 Cookie 无法读取同一会话。
- 第四次完整报告返回 429。
- 公开 Agent 工具列表为空。
- 现有 `workbuddy.inshocking.com` Basic Auth 和其他 Nginx 站点不受影响。

阶段提交：

```text
ci: deploy public fortune application
```

## 7. 最终验证矩阵

| 层 | 命令/检查 | 通过标准 |
| --- | --- | --- |
| 排盘服务 | `npm test && npm run build` | golden、边界、schema 全绿 |
| 后端 | `uv run pytest` | 现有和新增测试全绿 |
| 管理前端 | `npm test -- --run && npm run build` | 单测和生产构建通过 |
| 公开前端 | `npm test -- --run && npm run build && npm run test:e2e` | 功能和视觉测试通过 |
| 工作流 | GitHub Actions | 所有构建、上传、激活步骤绿色 |
| TLS | 公网 curl/浏览器 | 可信证书、HTTP 301、HTTPS 200 |
| 隔离 | 管理 API/跨会话探测 | 404/403，无数据泄露 |
| 生命周期 | 时间控制测试 | 24 小时清理完整 |
| 资源 | `docker stats`, `free -h` | 无 OOM，Swap 不持续增长 |

## 8. 风险与控制

| 风险 | 控制 |
| --- | --- |
| OpenFate 输出升级漂移 | 精确锁版本、golden diff、显式升级 |
| 匿名限额被代理绕过 | 访客 + IP HMAC、分钟限速、每日额度；第一版不声称绝对防刷 |
| 文件存储并发 | 单 worker、进程锁、原子替换 |
| 模型提示注入 | 固定可信上下文、无工具、公开路由隔离 |
| 2C2G 内存峰值 | 排盘 256 MB、后端 768 MB、GitHub runner 构建、2 GB Swap |
| 发布失败中断现网 | 分阶段健康检查、保留上一镜像和 release、失败回滚 |
| 出生隐私残留在日志 | 请求正文不记录、会话目录整体 TTL 删除、原始 IP 不落盘 |
| 命理解读造成误导 | 专业克制 Skill、固定免责声明、高风险主题降级 |

## 9. 执行顺序和提交边界

1. `feat: add deterministic bazi engine service`
2. `feat: add published app public runtime`
3. `feat: add published app management UI`
4. `feat: add public fortune experience`
5. `ci: deploy public fortune application`

每个提交必须满足本阶段测试，不能把红色测试留给后续提交修复。线上部署只在全部五个阶段和最终验证矩阵通过后执行。
