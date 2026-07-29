# Mini-workbuddy

Mini-workbuddy 是一个轻量级、本地优先的 Agent 工作台。它使用 FastAPI、Vue 和本地文件完成模型、工具、技能、智能体、会话与运行记录管理，不依赖外部数据库。

## 已实现能力

- DeepSeek 与阿里云百炼 Qwen 模型配置、密钥掩码和连通性测试。
- 固定的读文件、写文件和命令行工具；写入与命令执行每次都需要用户审批。
- Skill 新建、编辑、启停、目录查看和 ZIP 安全导入。
- Agent 新建与编辑、内置主 Agent、独立 `agent.md`、工具/技能绑定和独立工作目录。
- 多轮会话、OpenAI 兼容 Tool Calling、Skill 内容注入、SSE 运行事件与审批恢复。
- JSON、JSONL 和 Markdown 本地落盘，以及可回看的运行事件时间线。

## 目录

```text
frontend/   Vue + Vite + Tailwind CSS 前端
fortune-frontend/  知命/知梦公开站点
backend/    FastAPI 后端与测试
workspace/  首次启动自动创建的配置、技能、会话和运行数据
```

## 启动后端

推荐直接在项目根目录一键启动前后端：

```bash
./start.sh
```

脚本会在首次运行时自动安装缺失依赖，启动成功后访问 [http://127.0.0.1:5173](http://127.0.0.1:5173)。按 `Ctrl+C` 会同时停止前后端服务。

也可以分别启动。后端命令：

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

默认数据目录是项目根目录的 `workspace/`。可从 `backend/.env.example` 创建本地 `.env` 并覆盖路径、工具轮次和超时设置。

前端命令：

```bash
cd frontend
npm install
npm run dev
```

打开 [http://localhost:5173](http://localhost:5173)。Vite 会把 `/api` 请求代理到 `http://127.0.0.1:8001`。

公开站点单独启动：

```bash
cd fortune-frontend
npm install
npm run dev
```

打开 [http://127.0.0.1:5174/fortune](http://127.0.0.1:5174/fortune) 使用“知命”，或访问 [http://127.0.0.1:5174/dream](http://127.0.0.1:5174/dream) 使用“知梦”。两个应用共享匿名访客身份，但每日额度、会话和浏览器恢复 key 相互独立。公开会话保存 24 小时，访客也可以主动删除。

“知梦”使用本地版本化公版梦象索引和固定 Agent Prompt，运行时不联网且不开放工具。传统条目只作文化参照，心理与现实映照不是诊断或预言。Dream App 初始保持禁用，只有 40 案真实模型评测通过并完成人工抽查后才能在“发布应用”页面启用。

一键脚本默认使用前端端口 `5173` 和后端端口 `8001`。需要临时覆盖时可以执行：

```bash
MINI_WORKBUDDY_FRONTEND_PORT=5175 MINI_WORKBUDDY_BACKEND_PORT=8010 ./start.sh
```

## 使用顺序

1. 在“模型”页面编辑默认 DeepSeek 或 Qwen 配置，填写 API Key 并测试连接。
2. 在“技能”页面新建 Skill，或导入包含唯一 `SKILL.md` 的 ZIP 包。
3. 在“智能体”页面配置模型、`agent.md`、工具、技能和独立工作目录。
4. 打开智能体运行页开始会话。
5. 写文件或命令行调用出现时，检查参数并选择“允许一次”或“拒绝”。
6. 在“运行记录”中查看完整模型、工具和审批事件。

## 测试

```bash
cd backend
uv run pytest

cd ../frontend
npm test -- --run
npm run build

cd ../fortune-frontend
npm test -- --run
npm run build
npm run test:e2e -- tests/e2e/fortune.spec.ts tests/e2e/dream.spec.ts
```

知梦发布评测分两步进行。先用 workspace 中已配置的模型生成 40 案结果，输出只能位于 `/tmp`：

```bash
cd backend
uv run python evals/dream_eval.py \
  --model-id deepseek-default \
  --output /tmp/miniworkbuddy-dream-eval.json
```

逐案审阅输出，在每个 `manual_scores` 中为 `faithfulness`、`layering`、`personalization`、`actionability` 填写 0–2 分，再执行门禁检查：

```bash
uv run python evals/dream_eval.py --check /tmp/miniworkbuddy-dream-eval.json
```

引用、安全和注入检查必须全部为 2 分；人工维度总均值至少 1.6，且每个维度均值至少 1.4。任一检查未通过时命令返回非零状态，Dream App 必须保持禁用。来源与重建细节见 [docs/dream-reference-sources.md](docs/dream-reference-sources.md)。

## 生产部署

生产环境通过 GitHub Actions 测试并构建管理前端、知命公开前端、FastAPI 镜像和确定性排盘镜像，再经 SSH 上传到服务器。服务器只加载镜像并切换版本化静态目录，不执行源码构建。排盘容器只加入专用 Docker network，不发布宿主机端口。

部署文件位于 `deploy/`，工作流位于 `.github/workflows/deploy.yml`。GitHub 仓库需要配置以下 Actions Secrets：

- `SERVER_HOST`
- `SERVER_PORT`
- `SERVER_USER`
- `SERVER_SSH_KEY`

服务器的 `/opt/mini-workbuddy/.env` 必须至少包含：

```dotenv
FRONTEND_ORIGIN=https://workbuddy.inshocking.com
FORTUNE_ORIGIN=https://fortune.inshocking.com
PUBLIC_SESSION_SECRET=<独立高熵随机值>
PUBLIC_IP_HASH_SECRET=<另一个独立高熵随机值>
COMMAND_TIMEOUT_SECONDS=30
```

两个 HMAC 密钥不得相同，也不能使用仓库中的开发默认值。运行数据持久化在 `/opt/mini-workbuddy/workspace`，不能放入 release 目录。部署脚本会依次检查排盘服务和 FastAPI；任一检查失败时恢复上一版容器镜像和 `current` 静态目录链接。

首次启用公开站点时，将 `deploy/fortune-nginx.conf` 安装到服务器使用的 `conf.d` 目录，确认配置后 reload：

```bash
sudo cp deploy/fortune-nginx.conf /etc/nginx/conf.d/fortune.conf
sudo nginx -t
sudo systemctl reload nginx
```

随后在阿里云 DNS 添加 `fortune.inshocking.com -> 47.93.35.251`，并在解析生效后签发证书：

```bash
sudo certbot --nginx -d fortune.inshocking.com --redirect
sudo certbot renew --dry-run
```

上线后至少验证公开元数据、管理 API 隔离和两个容器的资源占用：

```bash
curl -I http://fortune.inshocking.com/
curl -I https://fortune.inshocking.com/
curl https://fortune.inshocking.com/api/public/apps/fortune
curl https://fortune.inshocking.com/api/public/apps/dream
curl -I https://fortune.inshocking.com/fortune
curl -I https://fortune.inshocking.com/dream
curl -I https://fortune.inshocking.com/api/models
docker stats --no-stream mini-workbuddy-backend fortune-bazi-engine
free -h
swapon --show
```

测试模型适配与 Agent 循环时使用假模型，不需要真实 API Key。真实对话和模型连通性测试需要在本地配置有效密钥。

Dream App 未完成发布评测或尚未手动启用时，`/api/public/apps/dream` 预期返回 404；静态 `/dream` 路由仍可部署，但不会绕过后端禁用状态。

## 文件与命令边界

- 所有文件路径在执行前解析，并必须位于当前 Agent 的工作目录内。
- 通过 `..`、绝对路径或符号链接逃逸工作目录会被拒绝。
- 命令默认在 Agent 工作目录中运行，并受超时与输出大小限制。
- 子进程环境会移除名称中包含 `KEY`、`TOKEN` 或 `SECRET` 的变量。
- Skill ZIP 会拒绝路径穿越、绝对路径、符号链接、多个 `SKILL.md` 入口和超限内容。
