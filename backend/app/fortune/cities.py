import json
from functools import lru_cache
from pathlib import Path

from app.errors import AppError


@lru_cache
def city_records() -> dict[str, dict]:
    path = Path(__file__).parent / "data" / "cities.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {record["code"]: record for record in payload["records"]}


def resolve_city(province_code: str, city_code: str) -> dict:
    records = city_records()
    province = records.get(province_code)
    city = records.get(city_code)
    if not province or province.get("level") != "province":
        raise AppError("INVALID_CITY", "省份代码无效", 422)
    if not city or city.get("level") != "city" or city.get("parent_code") != province_code:
        raise AppError("INVALID_CITY", "城市与省份不匹配", 422)
    return city
