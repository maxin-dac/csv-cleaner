from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Any


def new_change_id() -> str:
    return str(uuid.uuid4())


def is_null_like(value) -> bool:
    if value is None:
        return True
    s = str(value).strip().lower()
    return s in ("", "na", "n/a", "null", "none", "-", "--", "nan")


@dataclass
class Change:
    id: str
    kind: str
    column: str | None
    row_index: int | None
    before: Any
    after: Any
    rule: str
    confidence: float
    status: str = "pending"


@dataclass
class WarningMessage:
    key: str
    params: dict = field(default_factory=dict)


@dataclass
class ColumnProfile:
    name: str
    dtype_inferred: str
    confidence: float
    null_like_rate: float
    distinct: int
    samples: list
    flags: list
    numeric_thousands: str | None = None
    numeric_decimal: str | None = None


@dataclass
class DetectionResult:
    changes: list[Change] = field(default_factory=list)
    warnings: list[WarningMessage] = field(default_factory=list)
    blocked_export: bool = False
