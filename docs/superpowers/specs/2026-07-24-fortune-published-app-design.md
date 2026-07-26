# 知命公开 Agent 应用设计规格

日期：2026-07-24
状态：已完成交互式设计确认，等待书面规格审阅

## 1. 目标

在 Mini Workbuddy 中增加通用的 Published App 发布层，并交付第一个公开应用“知命”：一个基于八字四柱的匿名命理体验。

管理员继续在 `workbuddy.inshocking.com` 中配置模型、Skill、Agent 和发布状态。访客通过 `fortune.inshocking.com` 填写出生信息，先获得确定性结构化命盘，再由固定的 DeepSeek Agent 生成专业克制的解读，并在同一命盘上下文中连续追问。

成功交付必须满足：

- 排盘由确定性引擎完成，LLM 不计算或改写四柱事实。
- 公开访客不能选择 Agent、模型、Skill 或工具。
- 公开域名不能访问任何 Workbuddy 管理 API。
- 每位匿名访客每天最多完成 3 次测算。
- 出生资料、命盘、消息和公开运行记录在 24 小时后删除。
- 桌面和移动端都能完成填写、报告阅读和追问。
- 通过 GitHub Actions 自动测试、构建和部署到现有 2C2G 服务器。

## 2. 产品范围

### 2.1 第一版包含

- 八字四柱，输入只支持公历。
- 出生地点只支持中国大陆省级和地级城市。
- 性别为男或女，必选，用于大运顺逆规则。
- 出生时间可精确到分钟，也可选择“时辰不详”。
- 默认使用北京时间；时间已知时可选真太阳时校正。
- 确定性输出包含标准化时间、四柱、十神、藏干、五行、纳音、十二长生、大运和地支交互等引擎可用字段。
- Agent 初始报告、最多 20 条追问、24 小时内同浏览器恢复。
- Workbuddy“应用”管理页和通用 Published App 管理 API。
- 公开限额、限速、匿名会话隔离、主动删除和定期清理。
- HTTPS、独立 Nginx 站点和安全响应头。

### 2.2 第一版不包含

- 农历输入、港澳台或海外出生地点。
- 紫微斗数、星座、称骨、六爻或其他命理体系。
- 合婚、多人命盘比较或反推生辰。
- 正式注册账号、付费、订单、分享海报或公开社区。
- 医疗诊断、投资建议、法律结论、寿命和具体灾祸预测。
- 通用 MCP 注册与运行能力。OpenFate 引擎由发布层强制调用，不由模型发起 MCP 工具调用。
- 水平扩展、多节点配额协调或外部数据库。

## 3. 已确认的产品决策

| 主题 | 决策 |
| --- | --- |
| 命理体系 | 八字四柱 |
| 访问方式 | 公开匿名 |
| 免费额度 | 每个匿名访客每天 3 次完整测算 |
| 数据保留 | 24 小时 |
| 默认模型 | DeepSeek Chat |
| 主流程 | 结构化命盘报告 + 上下文追问 |
| 历法输入 | 只支持公历 |
| 地点范围 | 中国大陆城市 |
| 时间规则 | 北京时间默认，真太阳时可选 |
| 时辰不详 | 允许，生成三柱并隐藏依赖时柱的结论 |
| 性别 | 男/女必选 |
| 表达风格 | 专业克制，区分确定性事实与解释性观点 |
| 品牌 | 知命 |
| 公开域名 | `fortune.inshocking.com` |
| 视觉方向 | 深墨绿、朱砂红、冷白纸色和少量铜金的现代中文历书 |

## 4. 外部技术选择与许可证

### 4.1 OpenFate 确定性排盘

采用 OpenFate 的确定性引擎，不采用大型综合玄学运行时。

锁定的首版依赖：

- `@openfate/bazi-mcp@0.2.6` 作为契约和 Skill 参考。
- `@openfate/bazi-engine@1.1.1` 作为排盘实现。
- `@openfate/true-solar-time@4.0.2` 作为真太阳时实现。

三者按 OpenFate 仓库声明使用 MIT License。内部排盘服务直接调用：

- `calculateBaziChart`
- `detectInteractions`
- `calculateTrueSolarTime`

不启动 MCP server，也不让 Agent 决定是否调用排盘。页面和报告保留如下来源说明：

```text
排盘计算由 OpenFate.ai 确定性引擎提供
https://openfate.ai
```

计算政策固定为：

- `calendarType = solar`
- `timezoneId = Asia/Shanghai`
- `dstOffset = 0`
- `dayBoundaryMode = ZI_HOUR_23`
- 真太阳时默认关闭，仅在用户主动开启且时间已知时启用。

### 4.2 城市和经度数据

构建期从 GeoNames 中国数据提取省级和地级城市名称及中心点经度，生成项目内版本化的只读城市目录。GeoNames 数据使用 CC BY 许可，允许商业使用并要求署名。

项目保留：

- 数据生成脚本。
- 原始数据版本日期和校验值。
- 生成后的精简城市目录。
- GeoNames 署名和链接。

行政区代码和名称作为公开事实用于稳定标识；经度来自 GeoNames。运行时不调用地理编码 API，不收集精确地址或浏览器定位。

### 4.3 未采用候选

- `Horace-Maxwell/horosa-skill`：AGPL-3.0，离线运行时约需 5 GB，并依赖 Java、Python、Node 和多个服务，对当前服务器和第一版范围过重。
- `shizhilya/yuan`：当前仓库未声明许可证且覆盖六种体系，不直接复制。
- `cantian-ai/bazi-mcp`：ISC、功能丰富，但公开契约未明确满足本项目的真太阳时和计算政策要求。
- `6tail/lunar-python`：MIT、轻量且成熟，但本项目还需自行补齐真太阳时和更多排盘政策，因此作为后备方案而非首选。

## 5. 总体架构

```text
公开访客
  |
  v
fortune.inshocking.com
  |- 静态 Fortune Vue 应用
  `- /api/public/apps/fortune/*
              |
              v
Mini Workbuddy FastAPI 发布层
  |- 匿名身份与 Origin 校验
  |- 每日额度与分钟限速
  |- 出生输入校验
  |- 公开会话与 24 小时清理
  |- 强制排盘编排
  `- 固定 Fortune Agent 运行
        |                         |
        v                         v
fortune-bazi-engine          DeepSeek Chat
  |- OpenFate Bazi           固定 Agent + 固定 Skill
  |- True Solar Time         无工具权限
  `- 结构化 JSON             只解释可信命盘

workbuddy.inshocking.com
  |- Basic Auth
  |- 管理前端和管理 API
  `- 模型、Skill、Agent、Published App 管理
```

公开面与管理面共享一个 FastAPI 进程和持久化根目录，但使用不同路由、存储目录和 Nginx 虚拟主机。公开 Nginx 站点只代理精确前缀 `/api/public/apps/fortune/`，其他 `/api` 请求直接返回 404。

## 6. 模块边界

### 6.1 `apps` 管理域

负责 Published App 的配置，不处理访客运行：

- 应用 CRUD。
- Slug 唯一性。
- Agent 绑定与启停。
- 额度、TTL 和最大追问配置。
- 管理页面展示公开 URL 和健康状态。

### 6.2 `public_runtime` 公开域

负责：

- 解析和签发匿名访客 Cookie。
- Origin、请求体和字段校验。
- 读取已启用 Published App，并固定解析绑定 Agent。
- 每日额度预留、提交和释放。
- IP/访客分钟级限速。
- 公开会话所有权检查。
- 初始报告和追问 SSE。
- 屏蔽内部模型、Agent、Skill、工具和错误细节。

### 6.3 `fortune_chart` 编排域

负责：

- 从只读城市目录解析经度。
- 生成 OpenFate 输入。
- 调用内部排盘服务。
- 验证排盘响应结构和 attribution。
- 标准化为项目自己的稳定 `FortuneChart` 契约。
- 时辰不详时删除或标记依赖时柱的字段。

### 6.4 `fortune-bazi-engine` 内部服务

使用 Node 22 和内置 `node:http` 暴露最小 HTTP 接口：

```text
GET  /health
POST /chart
```

不引入 Web 框架，不保存数据，不记录出生请求正文，不映射宿主机端口，只能通过 Docker 内部 network 被 FastAPI 访问。

### 6.5 `fortune-frontend`

独立 Vue 3 + Vite 应用，不复用或打包管理后台路由。职责是：

- 获取公开应用元数据和剩余额度。
- 校验并提交出生表单。
- 渲染结构化命盘。
- 消费报告和追问 SSE。
- 恢复或主动删除当前匿名会话。
- 展示隐私、来源和文化娱乐免责声明。

## 7. Published App 数据模型

存储文件：`workspace/apps.json`。

```json
{
  "id": "fortune",
  "name": "知命",
  "slug": "fortune",
  "agent_id": "fortune-bazi-agent",
  "enabled": true,
  "public": true,
  "daily_limit": 3,
  "session_ttl_hours": 24,
  "max_questions": 20,
  "created_at": "2026-07-24T00:00:00Z",
  "updated_at": "2026-07-24T00:00:00Z"
}
```

管理 API：

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| `GET` | `/api/apps` | 列出应用 |
| `POST` | `/api/apps` | 创建应用 |
| `GET` | `/api/apps/{id}` | 获取应用 |
| `PUT` | `/api/apps/{id}` | 完整更新 |
| `DELETE` | `/api/apps/{id}` | 删除应用配置，不删除 Agent |

删除已存在公开会话的应用时，公开请求立即拒绝；会话仍按 TTL 清理，管理员删除应用不绕过数据生命周期。

## 8. 默认 Agent 和 Skill

首次部署幂等创建：

```text
Agent ID：fortune-bazi-agent
名称：知命 · 八字解读师
模型：现有 DeepSeek 模板
Skill：bazi-interpreter
工具：[]
```

模型模板没有 API Key 或被停用时，应用健康状态为 `model_unavailable`，公开运行返回 `MODEL_UNAVAILABLE`。启动过程不覆盖管理员后来修改的 API Key、Agent 模型绑定、提示词或 Skill 内容。

`bazi-interpreter` 是项目自有窄范围 Skill：

- 参考 OpenFate MIT Skill 的“确定性计算优先”和输入确认原则。
- 明确命盘 JSON 是只读可信事实。
- 禁止模型补算四柱、时柱、大运或真太阳时。
- 要求主要判断列出对应命盘依据。
- 要求区分确定性字段与解释性观点。
- 要求时辰不详时隐藏依赖时柱的判断。
- 保留 OpenFate attribution。
- 不复制未明确授权的现代命理文章或 Skill 文本。

公开运行在服务端再次强制 `tools=[]`，不信任 Agent 配置中的工具绑定。即使管理员误给该 Agent 绑定工具，公开发布层也不向模型发送工具定义。

## 9. 公开 API

公开域名只允许：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/api/public/apps/fortune` | 应用元数据、字段约束、免责声明、额度 |
| `POST` | `/api/public/apps/fortune/sessions` | 校验、排盘、创建匿名会话 |
| `GET` | `/api/public/apps/fortune/sessions/{id}` | 恢复当前访客的会话 |
| `POST` | `/api/public/apps/fortune/sessions/{id}/report` | 生成一次初始报告，SSE |
| `POST` | `/api/public/apps/fortune/sessions/{id}/messages` | 追问，SSE |
| `DELETE` | `/api/public/apps/fortune/sessions/{id}` | 立即删除会话所有数据 |

### 9.1 创建会话请求

```json
{
  "name": "可选昵称",
  "gender": "male",
  "birth_date": "1995-03-12",
  "birth_time": "08:30",
  "birth_time_unknown": false,
  "province_code": "110000",
  "city_code": "110100",
  "true_solar_time": true,
  "focus_topics": ["career", "relationship"]
}
```

验证规则：

- `birth_date` 为 1900-01-01 到服务器当前中国日期。
- `gender` 只能是 `male` 或 `female`。
- 省市代码必须是版本化城市目录中的合法父子关系。
- `birth_time_unknown=true` 时，`birth_time` 必须为空且 `true_solar_time=false`。
- `focus_topics` 最多 3 个，值只能来自 `career`、`wealth`、`relationship`、`growth`、`current_year`。
- `name` 可空，非空时去除首尾空白且不超过 30 个 Unicode 字符。
- JSON 请求体不超过 16 KB，未知字段被拒绝。

### 9.2 创建会话响应

```json
{
  "session": {
    "id": "uuid",
    "status": "chart_ready",
    "expires_at": "2026-07-25T10:00:00Z",
    "remaining_questions": 20
  },
  "quota": {
    "daily_limit": 3,
    "remaining": 2,
    "resets_at": "2026-07-25T00:00:00+08:00"
  },
  "chart": {
    "input": {},
    "calculation_policy": {},
    "pillars": {},
    "ten_gods": {},
    "hidden_stems": {},
    "five_elements": {},
    "da_yun": [],
    "interactions": [],
    "attribution": {}
  }
}
```

### 9.3 公开 SSE

只返回：

```text
run.started
message.delta
message.completed
run.completed
run.failed
```

事件不包含工具、审批、模型 ID、Agent ID、Skill 内容、工作目录或内部堆栈。断线产生的未完成文本不作为最终报告保存。

## 10. 匿名身份、配额与并发

匿名 Cookie：

```text
fortune_visitor=<随机签名令牌>
HttpOnly
Secure
SameSite=Lax
Path=/api/public/apps/fortune
Max-Age=2592000
```

Cookie 只保存随机身份，不保存出生资料。服务端使用不同密钥分别生成访客和 IP 的 HMAC 哈希，不保存原始 IP。

限制：

- 每个访客每天最多 3 次完成的初始报告。
- IP 与访客组合每天也最多 3 次，降低清 Cookie 绕过成本。
- 每个 IP 每分钟最多创建 5 个会话。
- 每个 IP 每分钟最多发送 10 条追问。
- 每个会话最多 20 条成功追问。
- 同一会话同一时刻只能有一个运行。

额度状态机：

```text
available -> reserved -> committed
                     `-> released
```

- 创建命盘成功后预留额度 15 分钟。
- 初始报告成功时提交额度。
- 排盘失败不预留。
- 模型失败、运行中断或 15 分钟未生成报告时释放。
- 删除已成功报告的会话不返还额度。

分钟级令牌桶在单进程内存中维护；每日额度存入 `workspace/public_usage/YYYY-MM-DD.json`，并由进程内异步锁保护原子更新。单 worker 是该一致性模型的前提。

## 11. 公开会话存储和生命周期

```text
workspace/public_sessions/<session-id>/
|- session.json
|- input.json
|- chart.json
|- messages.jsonl
`- runs/<run-id>.jsonl
```

`session.json` 保存访客 HMAC、状态、应用 ID、创建和过期时间、问题计数，不保存原始 IP。

状态：

```text
chart_ready
report_running
report_ready
report_failed
question_running
interrupted
expired
```

FastAPI lifespan 启动时立即扫描过期会话，并启动每 15 分钟一次的清理协程。清理删除整个会话目录，包括出生输入、命盘、消息和公开运行记录。应用只保留不含出生信息的按日聚合计数。

`DELETE` 接口校验所有权后立即删除目录；重复删除返回 404，避免暴露会话是否属于其他访客。

## 12. Agent 上下文和报告契约

每次模型调用按顺序构造：

1. 系统身份、表达风格、安全边界和固定报告结构。
2. `bazi-interpreter` Skill。
3. 后端校验后的只读结构化命盘，使用明确的数据边界标签。
4. 当前公开会话中已完成的用户和助手消息。
5. 当前关注方向或追问。

初始报告固定章节：

1. 输入确认
2. 排盘口径
3. 四柱命盘
4. 日主与五行态势
5. 十神与藏干重点
6. 格局总论
7. 性格优势与容易失衡之处
8. 事业与学习倾向
9. 财务观念与风险偏好
10. 关系与沟通模式
11. 当前大运
12. 未来三年趋势
13. 可执行的生活建议
14. 依据与免责声明

结构化命盘由前端直接渲染，不从模型 Markdown 反向解析。模型 Markdown 只承载第 6-14 节的解释内容，并通过 DOMPurify 清洗。

Agent 必须使用“倾向、可能、建议关注”等表达，列出主要依据，不得：

- 预测具体死亡、灾祸、严重疾病或犯罪。
- 判断胎儿性别、生育结果或寿命。
- 提供医疗诊断、投资买卖或法律结论。
- 宣称命理具有科学证明或百分之百准确。
- 制造恐惧并引导付费化解。
- 推断民族、宗教或其他敏感身份。
- 接受用户文本覆盖原始命盘。

高风险问题返回领域边界说明和现实世界安全建议。提示注入不被视为安全边界；真正边界是公开运行没有工具、没有管理 API 权限、没有文件访问和没有服务端密钥。

## 13. 前端体验

### 13.1 信息架构

第一屏直接显示出生表单，不设置营销 Hero：

- 品牌与今日剩余额度。
- 性别分段选择。
- 公历日期。
- 出生时间与“时辰不详”。
- 省、市选择器。
- 真太阳时开关和简短说明。
- 最多 3 个关注方向。
- 24 小时隐私说明。
- “开始排盘”主命令。

报告页：

- 结构化四柱和计算口径。
- 五行、十神、大运等可扫描事实。
- 固定章节导航。
- Agent 解读和依据块。
- 底部稳定尺寸的追问输入区。
- “立即清除资料”命令。

### 13.2 视觉规则

- 品牌名“知命”。
- 深墨绿导航和关键结构、朱砂红主操作、冷白纸色内容区、少量铜金用于计算口径和依据。
- 不使用紫色星空、金色渐变、装饰光球、营销 Hero 或嵌套卡片。
- 命盘和表单使用明确网格尺寸，动态内容不得推动四柱或输入控件变形。
- 桌面为表单/历书视觉与工作区并列；移动端为单列、底部拇指可达操作。
- 最终视觉资产使用具有明确授权的中国古代星图或历书局部位图，并在资源清单记录来源；没有合适授权资产时生成原创位图，不使用伪古籍扫描件。

## 14. 错误处理

| HTTP | 错误码 | 行为 |
| ---: | --- | --- |
| 400 | `INVALID_BIRTH_INPUT` | 表单定位到具体字段 |
| 403 | `ORIGIN_NOT_ALLOWED` | 不处理请求，不签发 Cookie |
| 404 | `PUBLIC_SESSION_NOT_FOUND` | 不区分不存在、过期或非所有者 |
| 409 | `REPORT_ALREADY_GENERATED` | 恢复已有报告 |
| 409 | `RUN_ALREADY_ACTIVE` | 保持当前运行 UI |
| 422 | `CHART_CALCULATION_FAILED` | 不扣额度、不调用模型 |
| 429 | `DAILY_QUOTA_EXCEEDED` | 显示中国时区重置时间 |
| 429 | `RATE_LIMITED` | 显示可重试秒数 |
| 502 | `MODEL_UNAVAILABLE` | 保留命盘并允许重新生成报告 |

错误继续使用项目统一 envelope：

```json
{
  "error": {
    "code": "DAILY_QUOTA_EXCEEDED",
    "message": "今天的 3 次测算额度已经用完",
    "details": {
      "resets_at": "2026-07-25T00:00:00+08:00"
    }
  }
}
```

服务重启将 `report_running` 和 `question_running` 改为 `interrupted`。刷新页面可恢复命盘和已完成消息，初始报告未成功时允许重试并释放额度预留。

## 15. 部署和服务器资源

GitHub Actions 顺序：

1. 后端单元和集成测试。
2. Workbuddy 前端测试与构建。
3. Fortune 前端测试与构建。
4. 排盘服务单元、契约和 smoke 测试。
5. 构建 FastAPI 和排盘服务两个 amd64 镜像。
6. 上传压缩镜像、两个前端产物和部署脚本。
7. 加载镜像并创建内部 Docker network。
8. 启动并检查排盘服务。
9. 启动并检查 FastAPI。
10. 原子切换前端 `current` 链接。
11. 任一健康检查失败则恢复上一版容器和链接。

服务器新增环境变量：

```text
PUBLIC_SESSION_SECRET=<独立随机 32 字节密钥>
PUBLIC_IP_HASH_SECRET=<不同的随机 32 字节密钥>
BAZI_ENGINE_URL=http://fortune-bazi-engine:3000
FORTUNE_ORIGIN=https://fortune.inshocking.com
```

只保存在 `/opt/mini-workbuddy/.env`，不提交到 GitHub。

Nginx：

- `workbuddy.inshocking.com` 保留 Basic Auth。
- `fortune.inshocking.com` 公开静态页面，仅代理精确公开 API 前缀。
- HTTP 重定向 HTTPS。
- SSE 关闭代理缓冲，读取超时 300 秒。
- 请求体限制 16 KB。
- 设置 CSP、`X-Content-Type-Options`、`Referrer-Policy` 和 frame 限制。
- 申请独立 Let's Encrypt 证书并沿用现有 Certbot cron 续期。

资源限制：

- FastAPI 保持单 worker 和 768 MB 上限。
- 排盘服务设置 256 MB 内存和 0.5 CPU 上限。
- 两个容器均使用 `10m x 3` 日志轮转。
- 现有 2 GB Swap 保留。

## 16. 测试与验收

### 16.1 排盘 golden cases

- 普通北京时间四柱。
- 真太阳时开启和关闭。
- 真太阳时校正后跨时辰。
- 23:00 子时换日边界。
- 节气交接前后。
- 时辰不详三柱模式。
- 男女大运顺逆。
- 中国大陆不同经度城市。
- 1900 年边界和当前日期边界。
- OpenFate 超时、错误和缺字段。

Golden case 结果必须同时与锁定引擎版本和至少一个公开 OpenFate 示例交叉验证。升级引擎只能通过显式依赖更新和 golden diff 审阅。

### 16.2 后端

- Published App CRUD、Slug 唯一性和 Agent 校验。
- 客户端无法提交或覆盖 Agent ID。
- Cookie 所有权和跨访客隔离。
- 每日 3 次、跨日重置和 15 分钟预留释放。
- IP 和访客分钟限速。
- 排盘和模型失败不误扣额度。
- 24 小时清理、主动删除和日志删除。
- Origin、Cookie 属性和请求体上限。
- 公开响应不泄露内部配置。
- 同会话并发互斥和重启中断恢复。
- SSE 事件顺序。
- 公开运行工具列表强制为空。
- 高风险问题和提示注入使用假模型测试。

### 16.3 前端

- 日期、性别、省市和关注方向校验。
- 时辰不详禁用时间和真太阳时。
- 额度和重置时间。
- 排盘、初始报告和追问 SSE。
- 会话恢复、过期和立即删除。
- 429、排盘失败、模型失败和断线状态。
- Markdown XSS 清洗。
- 320、390、768、1440 px 截图和无横向溢出检查。
- 动态内容不遮挡命盘、按钮或追问输入。

### 16.4 线上验收

- `fortune.inshocking.com` HTTPS 有效。
- 未登录访客可以完成排盘、报告和追问。
- 管理员可以启停应用和更换 Agent。
- 其他访客不能读取该会话。
- 每天第 4 次测算被拒绝。
- 24 小时过期资料完整清理。
- 公开域名访问管理 API 返回 404。
- GitHub Actions 全绿且失败部署能回滚。
- 当前 Workbuddy、博客、Pet 和既有 Next.js 服务不受影响。

## 17. 实施分解

实施按依赖顺序分为四个可验证子项目：

1. **确定性排盘服务**：锁定依赖、城市数据生成、内部 HTTP 契约和 golden cases。
2. **Published App 后端**：管理域、公开域、匿名身份、配额、TTL 和无工具 Agent 编排。
3. **管理与公开前端**：Workbuddy 应用管理页、知命表单、命盘、报告和追问体验。
4. **部署与上线**：双镜像工作流、回滚、Nginx、DNS、证书、线上安全和资源验证。

每个子项目通过对应测试后再进入下一个，最终以完整匿名用户流程作为端到端验收。

## 18. 参考资料

- OpenFate Bazi MCP：<https://github.com/openfate-ai/openfate-mcp>
- OpenFate Bazi MCP v0.2.6：<https://github.com/openfate-ai/openfate-mcp/releases/tag/v0.2.6>
- OpenFate：<https://openfate.ai>
- OpenFate 真太阳时说明：<https://openfate.ai/en/insights/true-solar-time>
- GeoNames 数据导出与许可：<https://www.geonames.org/export/>
- 6tail lunar-python：<https://github.com/6tail/lunar-python>
- Cantian Bazi MCP：<https://github.com/cantian-ai/bazi-mcp>
- Horosa Skill：<https://github.com/Horace-Maxwell/horosa-skill>
- Yuan Skill：<https://github.com/shizhilya/yuan>
