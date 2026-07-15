from datetime import UTC, datetime
from pathlib import Path

from app.storage.json_store import AtomicJsonStore


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def bootstrap_workspace(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for dirname in ("skills", "agents", "sessions", "runs", "runtime"):
        (root / dirname).mkdir(parents=True, exist_ok=True)

    created_at = utc_now()
    models = [
        {
            "id": "deepseek-default",
            "name": "DeepSeek 默认模型",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
            "api_key": "",
            "enabled": True,
            "temperature": 0.7,
            "max_tokens": 4096,
            "created_at": created_at,
            "updated_at": created_at,
        },
        {
            "id": "qwen-default",
            "name": "通义千问默认模型",
            "provider": "qwen",
            "model": "qwen-plus",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "",
            "enabled": True,
            "temperature": 0.7,
            "max_tokens": 4096,
            "created_at": created_at,
            "updated_at": created_at,
        },
    ]
    tools = [
        {
            "id": "read_file",
            "name": "读文件",
            "description": "读取智能体工作目录内的文本文件",
            "enabled": True,
            "approval_required": False,
        },
        {
            "id": "write_file",
            "name": "写文件",
            "description": "写入智能体工作目录内的文件",
            "enabled": True,
            "approval_required": True,
        },
        {
            "id": "run_command",
            "name": "命令行执行",
            "description": "在智能体工作目录内执行命令",
            "enabled": True,
            "approval_required": True,
        },
    ]
    agents = [
        {
            "id": "main-agent",
            "name": "主 Agent",
            "description": "系统内置的主智能体",
            "model_id": "deepseek-default",
            "tool_ids": ["read_file", "write_file", "run_command"],
            "skill_ids": [],
            "work_directory": str((root / "runtime" / "main-agent").resolve()),
            "enabled": True,
            "is_builtin": True,
            "created_at": created_at,
            "updated_at": created_at,
        }
    ]
    AtomicJsonStore(root / "models.json", models).ensure()
    AtomicJsonStore(root / "tools.json", tools).ensure()
    AtomicJsonStore(root / "agents.json", agents).ensure()
    (root / "agents" / "main-agent").mkdir(parents=True, exist_ok=True)
    (root / "runtime" / "main-agent").mkdir(parents=True, exist_ok=True)
    prompt_path = root / "agents" / "main-agent" / "agent.md"
    if not prompt_path.exists():
        prompt_path.write_text(
            "# 主 Agent\n\n你是一个谨慎、清晰的本地工作助手。\n",
            encoding="utf-8",
        )

