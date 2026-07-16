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
```

测试模型适配与 Agent 循环时使用假模型，不需要真实 API Key。真实对话和模型连通性测试需要在本地配置有效密钥。

## 文件与命令边界

- 所有文件路径在执行前解析，并必须位于当前 Agent 的工作目录内。
- 通过 `..`、绝对路径或符号链接逃逸工作目录会被拒绝。
- 命令默认在 Agent 工作目录中运行，并受超时与输出大小限制。
- 子进程环境会移除名称中包含 `KEY`、`TOKEN` 或 `SECRET` 的变量。
- Skill ZIP 会拒绝路径穿越、绝对路径、符号链接、多个 `SKILL.md` 入口和超限内容。
