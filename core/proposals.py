from __future__ import annotations
from core.models import DetectionResult, WarningMessage
from core.infer_types import infer_types, build_type_changes
from core.normalize_dates import normalize_dates
from core.normalize_text import normalize_text
from core.coherence import run_coherence
from core.duplicates import find_duplicates
from core.warning_keys import WARN_CONFLICT


PRIORITY = {
    "dedup": 0,
    "date_norm": 1,
    "cat_merge": 2,
    "text_norm": 3,
    "coherence_fix": 4,
    "type_cast": 5,
}


def resolve_conflicts(changes: list):
    cell: dict[tuple, list] = {}
    other: list = []
    for c in changes:
        if c.column is not None and c.row_index is not None:
            cell.setdefault((c.column, c.row_index), []).append(c)
        else:
            other.append(c)
    warnings: list = []
    kept: list = []
    for (col, row), group in cell.items():
        if len(group) == 1:
            kept.append(group[0])
            continue
        ordered = sorted(group, key=lambda c: (PRIORITY.get(c.kind, 99), c.id))
        winner = ordered[0]
        kept.append(winner)
        for loser in ordered[1:]:
            warnings.append(WarningMessage(WARN_CONFLICT, {"col": col, "row": row, "kept": winner.rule, "dropped": loser.rule}))
    kept.sort(key=lambda c: (c.row_index if c.row_index is not None else -1, str(c.column), c.kind))
    return other + kept, warnings


def aggregate(df, *, threshold: float = 0.95, case: str = "keep", cat_threshold: int = 90, unify_nulls: bool = True, dup_keys: list | None = None, dup_threshold: int = 85):
    profiles = infer_types(df, threshold=threshold)
    result = DetectionResult()
    result.changes.extend(build_type_changes(profiles))
    dr_dates = normalize_dates(df, profiles)
    result.changes.extend(dr_dates.changes)
    result.warnings.extend(dr_dates.warnings)
    result.blocked_export = result.blocked_export or dr_dates.blocked_export
    dr_text = normalize_text(df, profiles, case=case, cat_threshold=cat_threshold)
    result.changes.extend(dr_text.changes)
    result.warnings.extend(dr_text.warnings)
    occupied = {(c.column, c.row_index) for c in result.changes if c.column is not None and c.row_index is not None}
    dr_coh = run_coherence(df, profiles, occupied=occupied, unify_nulls=unify_nulls)
    result.changes.extend(dr_coh.changes)
    result.warnings.extend(dr_coh.warnings)
    if dup_keys:
        dr_dup = find_duplicates(df, dup_keys, threshold=dup_threshold)
        result.changes.extend(dr_dup.changes)
        result.warnings.extend(dr_dup.warnings)
        result.blocked_export = result.blocked_export or dr_dup.blocked_export
    final, conflict_warnings = resolve_conflicts(result.changes)
    result.changes = final
    result.warnings.extend(conflict_warnings)
    return profiles, result
