import json
from pathlib import Path

import pytest

from app.dream.references import DreamReferenceIndex
from app.errors import AppError


SOURCE = {
    "id": "zhougong-public-domain-v1",
    "upstream_commit": "1aa675597ee1405c9dea142bda0a3a9ed460ac99",
}


def symbol(
    symbol_id: str,
    label: str,
    aliases: list[str],
    *,
    category: str = "测试分类",
    quote: str = "测试原文。",
    source_id: str = "zhougong-public-domain-v1",
) -> dict:
    return {
        "id": symbol_id,
        "label": label,
        "aliases": aliases,
        "category": category,
        "quote": quote,
        "source_id": source_id,
    }


def write_index(tmp_path, symbols: list[dict], **overrides):
    payload = {
        "schema_version": 1,
        "version": "1.0.0",
        "source": SOURCE,
        "symbols": symbols,
    }
    payload.update(overrides)
    path = tmp_path / "dream-symbols.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "overrides",
    [
        {"schema_version": 2},
        {"version": None},
        {"source": None},
        {"source": {"id": "", "upstream_commit": "commit"}},
    ],
)
def test_load_rejects_invalid_schema_or_missing_source(tmp_path, overrides):
    path = write_index(tmp_path, [symbol("water", "水", ["水"])], **overrides)

    with pytest.raises(AppError) as captured:
        DreamReferenceIndex.load(path)

    assert captured.value.code == "DREAM_REFERENCE_UNAVAILABLE"
    assert captured.value.status_code == 503


def test_load_rejects_duplicate_symbol_ids(tmp_path):
    path = write_index(
        tmp_path,
        [symbol("water", "水", ["水"]), symbol("water", "河水", ["河水"])],
    )

    with pytest.raises(AppError, match="梦象资料暂不可用"):
        DreamReferenceIndex.load(path)


def test_load_rejects_symbol_without_source(tmp_path):
    item = symbol("water", "水", ["水"])
    item.pop("source_id")
    path = write_index(tmp_path, [item])

    with pytest.raises(AppError, match="梦象资料暂不可用"):
        DreamReferenceIndex.load(path)


def test_load_wraps_missing_and_malformed_files(tmp_path):
    missing = tmp_path / "missing.json"
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")

    for path in (missing, malformed):
        with pytest.raises(AppError) as captured:
            DreamReferenceIndex.load(path)
        assert captured.value.code == "DREAM_REFERENCE_UNAVAILABLE"


def test_matches_explicit_simplified_and_traditional_aliases(tmp_path):
    path = write_index(
        tmp_path,
        [symbol("dragon", "龙", ["龙", "龍", "巨龙", "巨龍"])],
    )
    index = DreamReferenceIndex.load(path)

    simplified = index.match("我梦见一条巨龙飞过")
    traditional = index.match("我夢見一條巨龍飛過")

    assert [(item.symbol_id, item.matched_text) for item in simplified] == [("dragon", "巨龙")]
    assert [(item.symbol_id, item.matched_text) for item in traditional] == [("dragon", "巨龍")]


def test_longest_alias_wins_without_matching_water_inside_fruit(tmp_path):
    path = write_index(
        tmp_path,
        [
            symbol("water", "水", ["水", "河水", "积水"]),
            symbol("fruit", "瓜果", ["水果", "果子"]),
        ],
    )
    index = DreamReferenceIndex.load(path)

    matches = index.match("桌上有很多水果，地上还有一片积水")

    assert [(item.symbol_id, item.matched_text) for item in matches] == [
        ("fruit", "水果"),
        ("water", "积水"),
    ]


def test_deduplicates_symbols_and_orders_by_first_selected_occurrence(tmp_path):
    path = write_index(
        tmp_path,
        [
            symbol("water", "水", ["水", "河水", "积水"]),
            symbol("house", "房屋", ["房屋", "屋子", "老宅"]),
        ],
    )
    index = DreamReferenceIndex.load(path)

    matches = index.match("先走进老宅，看见屋子漏水，院中又有河水和积水")

    assert [item.symbol_id for item in matches] == ["house", "water"]
    assert [item.matched_text for item in matches] == ["老宅", "水"]
    assert len(matches) == 2


def test_returns_at_most_eight_matches(tmp_path):
    symbols = [symbol(f"symbol-{index}", f"意象{index}", [f"意象{index}"]) for index in range(10)]
    path = write_index(tmp_path, symbols)
    index = DreamReferenceIndex.load(path)

    matches = index.match("、".join(item["label"] for item in symbols))

    assert [item.symbol_id for item in matches] == [f"symbol-{index}" for index in range(8)]


def test_returns_empty_list_when_no_alias_matches(tmp_path):
    path = write_index(tmp_path, [symbol("water", "水", ["水", "河水"])])

    assert DreamReferenceIndex.load(path).match("电梯在陌生星球上横向移动") == []


def test_runtime_index_avoids_single_character_false_positives_and_matches_explicit_phrases():
    path = (
        Path(__file__).parents[1]
        / "app/bootstrap/assets/dream-interpreter/references/dream-symbols.json"
    )
    index = DreamReferenceIndex.load(path)

    assert [item.symbol_id for item in index.match("小狗一路跟到门口")] == ["dog", "door"]
    assert index.match("我错过了伴侣乘坐的列车") == []
    assert [item.symbol_id for item in index.match("路边的棺材是不是说明有人马上要去世")] == [
        "road",
        "coffin",
    ]
    assert [item.symbol_id for item in index.match("已经离世的亲人在厨房做饭")] == ["death"]
    assert [item.symbol_id for item in index.match("我从高楼跳下后惊醒")] == ["falling"]
