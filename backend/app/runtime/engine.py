import json
from pathlib import Path
from typing import Any, AsyncIterator

from app.errors import AppError
from app.runtime.approvals import ApprovalBroker
from app.tools.executors import EXECUTORS


class AgentEngine:
    def __init__(self, adapter: Any, approvals: ApprovalBroker, max_rounds: int = 8) -> None:
        self.adapter = adapter
        self.approvals = approvals
        self.max_rounds = max_rounds

    async def run(
        self,
        model: dict[str, Any],
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        workspace: Path,
    ) -> AsyncIterator[dict[str, Any]]:
        enabled = {tool["id"] for tool in tools if tool.get("enabled")}
        for _ in range(self.max_rounds):
            response = await self.adapter.complete(model, messages, tools)
            content = response.get("content", "")
            calls = response.get("tool_calls", [])
            assistant_message: dict[str, Any] = {"role": "assistant", "content": content}
            if calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {"name": call["name"], "arguments": json.dumps(call["arguments"], ensure_ascii=False)},
                    }
                    for call in calls
                ]
            messages.append(assistant_message)
            if content:
                yield {"type": "message.delta", "data": {"content": content}}
            if not calls:
                yield {"type": "message.completed", "data": {"content": content}}
                yield {"type": "run.completed", "data": {}}
                return
            for call in calls:
                name = call["name"]
                arguments = call["arguments"]
                if name not in enabled or name not in EXECUTORS:
                    result: dict[str, Any] = {"error": "工具未授权或已停用"}
                    yield {"type": "tool.failed", "data": {"tool_call_id": call["id"], "name": name, "result": result}}
                else:
                    yield {"type": "tool.requested", "data": {"tool_call_id": call["id"], "name": name, "arguments": arguments}}
                    allowed = True
                    if name in {"write_file", "run_command"}:
                        approval = self.approvals.create(name, arguments)
                        yield {
                            "type": "approval.required",
                            "data": {
                                "approval_id": approval.id,
                                "tool_call_id": call["id"],
                                "name": name,
                                "arguments": arguments,
                            },
                        }
                        allowed = await approval.future
                        yield {
                            "type": "approval.resolved",
                            "data": {"approval_id": approval.id, "allowed": allowed},
                        }
                    if allowed:
                        try:
                            result = await EXECUTORS[name](workspace, arguments)
                            yield {"type": "tool.completed", "data": {"tool_call_id": call["id"], "name": name, "result": result}}
                        except AppError as error:
                            result = {"error": error.message, "code": error.code}
                            yield {"type": "tool.failed", "data": {"tool_call_id": call["id"], "name": name, "result": result}}
                    else:
                        result = {"error": "用户拒绝了本次工具调用", "code": "APPROVAL_REJECTED"}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
        yield {"type": "run.failed", "data": {"code": "TOOL_ROUND_LIMIT", "message": "工具调用轮次已达到上限"}}

