from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DreamEmotion(StrEnum):
    FEAR = "害怕"
    ANXIETY = "焦虑"
    PEACE = "平静"
    SURPRISE = "惊奇"
    NOSTALGIA = "怀念"
    SADNESS = "悲伤"
    JOY = "愉悦"
    CONFUSION = "困惑"


class DreamInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dream_text: str = Field(min_length=20, max_length=4000)
    emotions: list[DreamEmotion] = Field(default_factory=list, max_length=3)
    recurring: bool = Field(default=False, strict=True)
    recent_context: str | None = Field(default=None, max_length=500)

    @field_validator("dream_text", mode="before")
    @classmethod
    def strip_dream_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("emotions", mode="before")
    @classmethod
    def deduplicate_emotions(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return value
        deduplicated = []
        for item in value:
            if item not in deduplicated:
                deduplicated.append(item)
        return deduplicated

    @field_validator("recent_context", mode="before")
    @classmethod
    def strip_recent_context(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("recent_context must not be blank")
        return stripped
