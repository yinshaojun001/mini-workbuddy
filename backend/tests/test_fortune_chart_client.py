import httpx
import pytest

from app.errors import AppError
from app.fortune.chart_client import ChartClient
from app.fortune.cities import resolve_city
from app.fortune.models import BirthInput


def birth_input():
    return BirthInput.model_validate(
        {
            "gender": "female",
            "birth_date": "1998-12-13",
            "birth_time": "12:00",
            "birth_time_unknown": False,
            "province_code": "110000",
            "city_code": "110100",
            "true_solar_time": False,
            "focus_topics": ["career"],
        }
    )


def test_city_resolution_checks_parent_relationship():
    assert 115 < resolve_city("110000", "110100")["longitude"] < 118
    with pytest.raises(AppError, match="城市与省份不匹配"):
        resolve_city("110000", "310100")


async def test_chart_client_returns_only_valid_envelopes():
    async def handler(request: httpx.Request):
        payload = __import__("json").loads(request.content)
        assert payload["birth_date"] == "1998-12-13"
        return httpx.Response(
            200,
            json={
                "chart": {
                    "pillars": {},
                    "day_master": {},
                    "da_yun": {},
                    "interactions": [],
                    "solar_time": None,
                    "calendar": {},
                    "metadata": {},
                },
                "policy": {},
                "attribution": {},
            },
        )

    result = await ChartClient("http://engine", httpx.MockTransport(handler)).calculate(birth_input(), 116.4)
    assert result["chart"]["pillars"] == {}


async def test_chart_client_rejects_incomplete_success_payloads():
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"chart": {}, "policy": {}, "attribution": {}}))
    with pytest.raises(AppError) as error:
        await ChartClient("http://engine", transport).calculate(birth_input(), 116.4)
    assert error.value.code == "CHART_CALCULATION_FAILED"


async def test_chart_client_maps_internal_failures_to_public_error():
    transport = httpx.MockTransport(lambda _: httpx.Response(500, text="internal stack"))
    with pytest.raises(AppError) as error:
        await ChartClient("http://engine", transport).calculate(birth_input(), 116.4)
    assert error.value.code == "CHART_CALCULATION_FAILED"
    assert "internal stack" not in error.value.message
