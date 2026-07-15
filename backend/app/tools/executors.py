import asyncio
import os
from pathlib import Path
from time import monotonic
from typing import Any

from app.errors import AppError

MAX_READ_BYTES = 1024 * 1024
MAX_OUTPUT_CHARS = 100_000


def resolve_in_workspace(root: Path, target: str) -> Path:
    resolved_root = root.expanduser().resolve()
    candidate = Path(target).expanduser()
    if not candidate.is_absolute():
        candidate = resolved_root / candidate
    resolved = candidate.resolve(strict=False)
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise AppError("PATH_OUTSIDE_WORKSPACE", "路径超出智能体工作目录", 403)
    return resolved


async def read_file(root: Path, arguments: dict[str, Any]) -> dict[str, Any]:
    path = resolve_in_workspace(root, str(arguments.get("path", "")))
    if not path.is_file():
        raise AppError("FILE_NOT_FOUND", "文件不存在", 404)
    if path.stat().st_size > MAX_READ_BYTES:
        raise AppError("FILE_TOO_LARGE", "文件超过读取大小限制", 413)
    data = await asyncio.to_thread(path.read_bytes)
    if b"\0" in data:
        raise AppError("BINARY_FILE", "暂不支持读取二进制文件", 422)
    return {"path": str(path.relative_to(root.resolve())), "content": data.decode("utf-8")}


async def write_file(root: Path, arguments: dict[str, Any]) -> dict[str, Any]:
    path = resolve_in_workspace(root, str(arguments.get("path", "")))
    content = str(arguments.get("content", ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(path.write_text, content, encoding="utf-8")
    return {"path": str(path.relative_to(root.resolve())), "bytes": len(content.encode())}


async def run_command(root: Path, arguments: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    command = arguments.get("command")
    if isinstance(command, list) and all(isinstance(part, str) for part in command):
        process_args = command
        shell = False
    elif isinstance(command, str) and command.strip():
        process_args = command
        shell = True
    else:
        raise AppError("INVALID_COMMAND", "命令不能为空", 422)
    safe_env = {key: value for key, value in os.environ.items() if "KEY" not in key and "TOKEN" not in key and "SECRET" not in key}
    started = monotonic()
    try:
        if shell:
            process = await asyncio.create_subprocess_shell(
                process_args,
                cwd=root,
                env=safe_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            process = await asyncio.create_subprocess_exec(
                *process_args,
                cwd=root,
                env=safe_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        raise AppError("COMMAND_TIMEOUT", "命令执行超时", 408) from exc
    return {
        "exit_code": process.returncode,
        "stdout": stdout.decode(errors="replace")[:MAX_OUTPUT_CHARS],
        "stderr": stderr.decode(errors="replace")[:MAX_OUTPUT_CHARS],
        "duration_ms": round((monotonic() - started) * 1000),
    }


EXECUTORS = {"read_file": read_file, "write_file": write_file, "run_command": run_command}

