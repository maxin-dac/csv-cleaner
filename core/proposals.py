from __future__ import annotations
from core.models import Change, DetectionResult
from core.infer_types import infer_types, build_type_changes
from core.normalize_dates import normalize_dates
from core.normalize_text import normalize_text
from core.coherence import run_coherence
from core.duplicates import find_duplicates


PRIORITY = {
    "dedup": 50,
    "date_norm": 40,
    "cat_merge": 30,
    "text_norm": 20,
    "coherence_fix": 10,
    "type_cast": 0,
}


def resolve_conflicts(changes: list[Change]):
    cell: dict[tuple, list[Change]] = {}
    other: list[Change] = []
    for c in changes:
        if c.column is not None and c.row_index is not None:
            cell.setdefault((c.column, c.row_index), []).append(c)
        else:
            other.append(c)
    warnings: list[str] = []
    kept: list[Change] = []
    for key, group in cell.items():
        if len(group) == 1:
            kept.append(group[0])
            continue
        group_sorted = sorted(group, key=lambda c: (-PRIORITY.get(c.kind, 0), c.id))
        winner = group_sorted[0]
        kept.append(winner)
        losers = [c.rule for c in group_sorted[1:]]
        warnings.append(f"conflict on {key[0]}@{key[1]}: kept {winner.rule}, dropped {losers}")
    kept.sort(key=lambda c: (c.row_index if c.row_index is not None else -1, str(c.column), c.kind))
    return other + kept, warnings


def aggregate(df, *, threshold: float = 0.95, case: str = "keep", cat_threshold: int = 90,
              unify_nulls: bool = True, dup_keys: list[str] | None = None, dup_threshold: int = 85):
    profiles = infer_types(df, threshold=threshold)
    dr = DetectionResult()
    dr.extend(DetectionResult(changes=build_type_changes(profiles)))
    dr.extend(normalize_dates(df, profiles))
    dr.extend(normalize_text(df, profiles, case=case, cat_threshold=cat_threshold))
    occupied = {(c.column, c.row_index) for c in dr.changes if c.column is not None and c.row_index is not None}
    dr.extend(run_coherence(df, profiles, occupied=occupied, unify_nulls=unify_nulls))
    if dup_keys:
        dr.extend(find_duplicates(df, dup_keys, threshold=dup_threshold))
    final, cw = resolve_conflicts(dr.changes)
    return profiles, DetectionResult(changes=final, warnings=dr.warnings + cw, blocked_export=dr.blocked_export)


def summary(changes: list[Change]) -> dict:
    counts: dict[str, int] = {}
    for c in changes:
        counts[c.kind] = counts.get(c.kind, 0) + 1
    return counts


def partition(changes: list[Change]):
    accepted = [c for c in changes if c.status == "accepted"]
    rejected = [c for c in changes if c.status == "rejected"]
    pending = [c for c in changes if c.status == "pending"]
    return accepted, rejected, pending