from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


NULL_TOKENS = {"", "na", "n/a", "null", "none", "nan", "-", "--", "–", "—", "?"}


def is_null_like(value: Any) -> bool:
    if value is None:
        return True
    try:
        if value != value:
            return True
    except Exception:
        pass
    return str(value).strip().lower() in NULL_TOKENS


@dataclass
class ColumnProfile:
    name: str
    dtype_inferred: str
    confidence: float
    null_like_rate: float
    distinct: int
    samples: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    numeric_thousands: str | None = None
    numeric_decimal: str | None = None


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

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"


def new_change_id() -> str:
    return uuid4().hex


@dataclass
class DetectionResult:
    changes: list[Change] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocked_export: bool = False

    def extend(self, other: DetectionResult) -> None:
        self.changes.extend(other.changes)
        self.warnings.extend(other.warnings)
        self.blocked_export = self.blocked_export or other.blocked_export