import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.errors import AppError


@dataclass
class PendingApproval:
    id: str
    tool_name: str
    arguments: dict[str, Any]
    future: asyncio.Future[bool]


class ApprovalBroker:
    def __init__(self) -> None:
        self.pending: dict[str, PendingApproval] = {}

    def create(self, tool_name: str, arguments: dict[str, Any]) -> PendingApproval:
        approval = PendingApproval(
            id=str(uuid4()),
            tool_name=tool_name,
            arguments=arguments,
            future=asyncio.get_running_loop().create_future(),
        )
        self.pending[approval.id] = approval
        return approval

    def resolve(self, approval_id: str, allowed: bool) -> None:
        approval = self.pending.pop(approval_id, None)
        if approval is None or approval.future.done():
            raise AppError("APPROVAL_NOT_PENDING", "审批不存在或已处理", 409)
        approval.future.set_result(allowed)

