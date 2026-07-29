from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class PreparedPublicContext:
    input_data: dict[str, Any]
    context: dict[str, Any]


class PublicAppAdapter(Protocol):
    id: str
    invalid_input_code: str
    invalid_input_message: str

    def health(self) -> str: ...

    def metadata(self, app: dict[str, Any]) -> dict[str, Any]: ...

    async def prepare(self, payload: dict[str, Any]) -> PreparedPublicContext: ...

    def public_context(self, context: dict[str, Any]) -> dict[str, Any]: ...

    def prompt_blocks(
        self, input_data: dict[str, Any], context: dict[str, Any]
    ) -> list[str]: ...

    def report_instruction(self) -> str: ...
