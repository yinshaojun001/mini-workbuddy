import json
from datetime import UTC, datetime

import pytest

from app.config import Settings
from app.errors import AppError
from app.public_runtime.adapters.fortune import FortunePublicAdapter
from tests.test_public_runtime_api import FakeChartClient, birth_payload


@pytest.mark.asyncio
async def test_fortune_adapter_prepares_chart_metadata_and_prompt(tmp_path):
    adapter = FortunePublicAdapter(
        Settings(workspace_dir=tmp_path),
        FakeChartClient(),
    )

    metadata = adapter.metadata({})
    beijing = next(item for item in metadata["locations"] if item["code"] == "110100")
    assert beijing == {
        "code": "110100",
        "parent_code": "110000",
        "name": "北京市",
        "level": "city",
    }

    prepared = await adapter.prepare(birth_payload())
    assert prepared.context["kind"] == "fortune"
    assert prepared.context["pillars"]["year"]["ganZhi"] == "戊寅"
    assert prepared.input_data["birth_date"] == "1998-12-13"
    assert adapter.public_context(prepared.context) == prepared.context
    assert adapter.report_instruction() == "请根据可信命盘生成完整的初始解读报告。"

    block = adapter.prompt_blocks(prepared.input_data, prepared.context)[0]
    assert block.count("<TRUSTED_FORTUNE_DATA>") == 1
    payload = json.loads(block.split("<TRUSTED_FORTUNE_DATA>\n", 1)[1].split("\n</", 1)[0])
    assert payload["birth_input"]["focus_topics"] == ["career"]
    assert payload["chart"]["pillars"]["year"]["ganZhi"] == "戊寅"
    assert "kind" not in payload["chart"]

    year = datetime.now(UTC).year
    context = {
        **prepared.context,
        "day_master": {"char": "甲", "element": "wood", "polarity": "yang"},
        "da_yun": {"cycles": [{"startYear": year - 1, "endYear": year + 8}]},
    }
    current_block = adapter.prompt_blocks(prepared.input_data, context)[0]
    current_payload = json.loads(
        current_block.split("<TRUSTED_FORTUNE_DATA>\n", 1)[1].split("\n</", 1)[0]
    )
    assert current_payload["current_context"]["current_year"] == year
    assert current_payload["current_context"]["current_da_yun"]["startYear"] == year - 1


@pytest.mark.asyncio
async def test_fortune_adapter_maps_model_validation_to_public_error(tmp_path):
    adapter = FortunePublicAdapter(Settings(workspace_dir=tmp_path), FakeChartClient())

    with pytest.raises(AppError) as captured:
        await adapter.prepare({**birth_payload(), "birth_time_unknown": True})

    assert captured.value.code == "INVALID_BIRTH_INPUT"
    assert captured.value.status_code == 422
    assert captured.value.details["fields"]
