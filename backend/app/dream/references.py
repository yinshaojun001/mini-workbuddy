from dataclasses import dataclass
import json
from pathlib import Path
import unicodedata

from app.errors import AppError


@dataclass(frozen=True)
class DreamReferenceMatch:
    symbol_id: str
    label: str
    matched_text: str
    match_type: str
    category: str
    quote: str
    source_id: str


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


class DreamReferenceIndex:
    def __init__(self, version: str, source: dict[str, str], symbols: list[dict]) -> None:
        self.version = version
        self.source = source
        self.symbols = symbols
        aliases: list[tuple[str, dict, bool, int]] = []
        for symbol in symbols:
            normalized_label = normalize_text(symbol["label"])
            for position, alias in enumerate(symbol["aliases"]):
                normalized_alias = normalize_text(alias)
                aliases.append(
                    (normalized_alias, symbol, normalized_alias == normalized_label, position)
                )
        self.aliases = sorted(aliases, key=lambda item: (-len(item[0]), item[3]))

    @classmethod
    def load(cls, path: Path) -> "DreamReferenceIndex":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cls._validate_payload(payload)
        except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
            raise cls._unavailable() from exc
        return cls(payload["version"], payload["source"], payload["symbols"])

    @staticmethod
    def _unavailable() -> AppError:
        return AppError("DREAM_REFERENCE_UNAVAILABLE", "梦象资料暂不可用", 503)

    @classmethod
    def _validate_payload(cls, payload: object) -> None:
        if not isinstance(payload, dict):
            raise ValueError("index must be an object")
        if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
            raise ValueError("unsupported schema")
        if not cls._nonempty_string(payload.get("version")):
            raise ValueError("missing version")

        source = payload.get("source")
        if not isinstance(source, dict) or not all(
            cls._nonempty_string(source.get(field)) for field in ("id", "upstream_commit")
        ):
            raise ValueError("missing source")

        symbols = payload.get("symbols")
        if not isinstance(symbols, list):
            raise ValueError("symbols must be a list")
        ids: set[str] = set()
        required_strings = ("id", "label", "category", "quote", "source_id")
        for symbol in symbols:
            if not isinstance(symbol, dict):
                raise ValueError("symbol must be an object")
            if not all(cls._nonempty_string(symbol.get(field)) for field in required_strings):
                raise ValueError("symbol fields are incomplete")
            if symbol["id"] in ids:
                raise ValueError("duplicate symbol id")
            ids.add(symbol["id"])
            if symbol["source_id"] != source["id"]:
                raise ValueError("unknown symbol source")
            aliases = symbol.get("aliases")
            if (
                not isinstance(aliases, list)
                or not aliases
                or not all(cls._nonempty_string(alias) for alias in aliases)
            ):
                raise ValueError("aliases must be non-empty strings")

    @staticmethod
    def _nonempty_string(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def match(self, dream_text: str, limit: int = 8) -> list[DreamReferenceMatch]:
        if limit <= 0:
            return []
        normalized = normalize_text(dream_text)
        candidates: list[tuple[int, int, str, dict, bool]] = []
        for alias, symbol, is_label, _ in self.aliases:
            start = normalized.find(alias)
            while start >= 0:
                candidates.append((start, start + len(alias), alias, symbol, is_label))
                start = normalized.find(alias, start + 1)

        candidates.sort(key=lambda item: (-(item[1] - item[0]), item[0]))
        occupied: list[tuple[int, int]] = []
        selected: dict[str, tuple[int, DreamReferenceMatch]] = {}
        for start, end, _, symbol, is_label in candidates:
            if any(start < used_end and end > used_start for used_start, used_end in occupied):
                continue
            occupied.append((start, end))
            match = (
                start,
                DreamReferenceMatch(
                    symbol_id=symbol["id"],
                    label=symbol["label"],
                    matched_text=normalized[start:end],
                    match_type="label" if is_label else "alias",
                    category=symbol["category"],
                    quote=symbol["quote"],
                    source_id=symbol["source_id"],
                ),
            )
            previous = selected.get(symbol["id"])
            if previous is None or start < previous[0]:
                selected[symbol["id"]] = match
        ordered = sorted(selected.values(), key=lambda pair: pair[0])
        return [item[1] for item in ordered[:limit]]
