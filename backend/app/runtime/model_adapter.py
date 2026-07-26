import json
from typing import Any

import httpx

from app.errors import AppError


def raise_for_model_status(response: httpx.Response) -> None:
    if response.status_code == 400:
        raise AppError("MODEL_REQUEST_INVALID", "模型名称或请求参数不兼容", 400)
    if response.status_code in {401, 403}:
        raise AppError("MODEL_AUTH_FAILED", "模型鉴权失败", 400)
    if response.status_code == 402:
        raise AppError("MODEL_BALANCE_INSUFFICIENT", "模型账户余额不足", 400)
    if response.status_code == 429:
        raise AppError("MODEL_RATE_LIMITED", "模型请求达到限流", 400)
    response.raise_for_status()


class OpenAICompatibleAdapter:
    async def complete(
        self,
        model: dict[str, Any],
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not model.get("api_key"):
            raise AppError("MODEL_API_KEY_MISSING", "模型尚未配置 API Key", 422)
        payload: dict[str, Any] = {
            "model": model["model"],
            "messages": messages,
            "temperature": model.get("temperature", 0.7),
            "max_tokens": model.get("max_tokens", 4096),
        }
        if tools:
            payload["tools"] = [tool_schema(tool["id"]) for tool in tools]
            payload["tool_choice"] = "auto"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    model["base_url"].rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {model['api_key']}"},
                    json=payload,
                )
            raise_for_model_status(response)
            message = response.json()["choices"][0]["message"]
        except AppError:
            raise
        except httpx.TimeoutException as exc:
            raise AppError("MODEL_TIMEOUT", "模型响应超时", 408) from exc
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise AppError("MODEL_RESPONSE_INVALID", "模型响应异常", 502) from exc
        calls = []
        for call in message.get("tool_calls") or []:
            try:
                arguments = json.loads(call["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}
            calls.append(
                {
                    "id": call["id"],
                    "name": call["function"]["name"],
                    "arguments": arguments,
                }
            )
        return {"content": message.get("content") or "", "tool_calls": calls}


def tool_schema(tool_id: str) -> dict[str, Any]:
    schemas = {
        "read_file": {
            "description": "读取工作目录内的文本文件",
            "properties": {"path": {"type": "string", "description": "相对文件路径"}},
            "required": ["path"],
        },
        "write_file": {
            "description": "写入工作目录内的文本文件，需要用户审批",
            "properties": {
                "path": {"type": "string", "description": "相对文件路径"},
                "content": {"type": "string", "description": "完整文件内容"},
            },
            "required": ["path", "content"],
        },
        "run_command": {
            "description": "在工作目录内执行命令，需要用户审批",
            "properties": {"command": {"type": ["string", "array"], "description": "命令字符串或参数数组"}},
            "required": ["command"],
        },
    }
    body = schemas[tool_id]
    return {
        "type": "function",
        "function": {
            "name": tool_id,
            "description": body["description"],
            "parameters": {"type": "object", "properties": body["properties"], "required": body["required"]},
        },
    }
