from __future__ import annotations
from core.models import DetectionResult
from core.infer_types import infer_types
from core.normalize_dates import normalize_dates
from core.normalize_text import normalize_text
from core.coherence import run_coherence
from core.duplicates import find_duplicates


def resolve_conflicts(result: DetectionResult) -> None:
    priority = {
        "dedup": 0,
        "date_norm": 1,
        "cat_merge": 2,
        "text_norm": 3,
        "coherence_fix": 4,
        "type_cast": 5,
    }
    by_cell: dict[tuple[str | None, int | None], list[int]] = {}
    for i, c in enumerate(result.changes):
        key = (c.column, c.row_index)
        if key not in by_cell:
            by_cell[key] = []
        by_cell[key].append(i)
    for key, indices in by_cell.items():
        if len(indices) < 2:
            continue
        sorted_indices = sorted(indices, key=lambda i: priority.get(result.changes[i].kind, 99))
        winner = sorted_indices[0]
        for i in sorted_indices[1:]:
            result.warnings.append(f"conflict at {key}: kept {result.changes[winner].kind}, discarded {result.changes[i].kind}")


def aggregate(
    df,
    *,
    threshold: float = 0.95,
    case: str = "keep",
    cat_threshold: int = 90,
    unify_nulls: bool = True,
    dup_keys: list[str] | None = None,
    dup_threshold: int = 85,
) -> tuple[dict, DetectionResult]:
    profiles, dr_types = infer_types(df, threshold=threshold)
    dr_dates = normalize_dates(df, profiles)
    dr_text = normalize_text(df, profiles, case=case, cat_threshold=cat_threshold)
    occupied = {(c.column, c.row_index) for c in dr_dates.changes if c.column is not None}
    dr_coh = run_coherence(df, profiles, occupied=occupied, unify_nulls=unify_nulls)
    result = DetectionResult()
    result.changes.extend(dr_types.changes)
    result.changes.extend(dr_dates.changes)
    result.changes.extend(dr_text.changes)
    result.changes.extend(dr_coh.changes)
    result.warnings.extend(dr_coh.warnings)
    if dup_keys:
        dr_dup = find_duplicates(df, dup_keys, threshold=dup_threshold)
        result.changes.extend(dr_dup.changes)
        result.warnings.extend(dr_dup.warnings)
    resolve_conflicts(result)
    result.blocked_export = any("ambiguous" in w for w in result.warnings if isinstance(w, str))
    return profiles, result
