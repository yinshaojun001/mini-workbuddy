from typing import Any

import httpx

from app.errors import AppError
from app.fortune.models import BirthInput
from app.fortune.models import EngineChartEnvelope


class ChartClient:
    def __init__(self, base_url: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    async def calculate(self, birth: BirthInput, longitude: float) -> dict[str, Any]:
        payload = {
            "birth_date": birth.birth_date.isoformat(),
            "birth_time": birth.birth_time.strftime("%H:%M") if birth.birth_time else None,
            "birth_time_unknown": birth.birth_time_unknown,
            "gender": birth.gender,
            "longitude": longitude,
            "true_solar_time": birth.true_solar_time,
        }
        timeout = httpx.Timeout(10, connect=2)
        try:
            async with httpx.AsyncClient(timeout=timeout, transport=self.transport) as client:
                response = await client.post(f"{self.base_url}/chart", json=payload)
                response.raise_for_status()
                result = response.json()
            return EngineChartEnvelope.model_validate(result).model_dump(mode="json")
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise AppError("CHART_CALCULATION_FAILED", "排盘服务暂时不可用", 422) from exc
