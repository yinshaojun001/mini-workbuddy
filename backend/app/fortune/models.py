from datetime import date, time
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BirthInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=30)
    gender: Literal["male", "female"]
    birth_date: date = Field(ge=date(1900, 1, 1))
    birth_time: time | None
    birth_time_unknown: bool
    province_code: str = Field(pattern=r"^\d{6}$")
    city_code: str = Field(pattern=r"^\d{6}$")
    true_solar_time: bool = False
    focus_topics: list[Literal["career", "wealth", "relationship", "growth", "current_year"]] = Field(
        default_factory=list, max_length=3
    )

    @field_validator("birth_time", mode="before")
    @classmethod
    def validate_birth_time_format(cls, value):
        if value is not None and (not isinstance(value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value)):
            raise ValueError("birth_time must use HH:mm")
        return value

    @model_validator(mode="after")
    def validate_time(self):
        if self.birth_time_unknown and (self.birth_time is not None or self.true_solar_time):
            raise ValueError("unknown birth time requires null time and disables true solar time")
        if not self.birth_time_unknown and self.birth_time is None:
            raise ValueError("birth time is required")
        if self.name is not None:
            self.name = self.name.strip() or None
        if len(set(self.focus_topics)) != len(self.focus_topics):
            raise ValueError("focus topics must be unique")
        return self


class EngineChart(BaseModel):
    model_config = ConfigDict(extra="allow")

    pillars: dict[str, Any]
    day_master: dict[str, Any]
    da_yun: dict[str, Any]
    interactions: list[dict[str, Any]]
    solar_time: dict[str, Any] | None
    calendar: dict[str, Any]
    metadata: dict[str, Any]


class EngineChartEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chart: EngineChart
    policy: dict[str, Any]
    attribution: dict[str, Any]
