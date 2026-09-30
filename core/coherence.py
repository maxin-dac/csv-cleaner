from __future__ import annotations
from dataclasses import dataclass, field
from core.models import Change, DetectionResult, new_change_id, is_null_like


@dataclass
class CoherenceContext:
    occupied: set = field(default_factory=set)
    unify_nulls: bool = True


def _check_null_unify(df, profiles, ctx):
    changes = []
    if not ctx.unify_nulls:
        return changes, []
    for col in df.columns:
        col = str(col)
        series = df[col].astype(object).tolist()
        for i, v in enumerate(series):
            if not is_null_like(v):
                continue
            if (col, i) in ctx.occupied:
                continue
            original = str(v)
            if original.strip() == "":
                continue
            changes.append(Change(new_change_id(), "coherence_fix", col, i, original, "", "null:unify", 1.0))
    return changes, []


def _check_ambiguous(df, profiles, ctx):
    warnings = []
    for col, p in profiles.items():
        if p.dtype_inferred == "string" and "numeric_locale_ambiguous" in p.flags:
            warnings.append(f"column {col} kept as string: numeric locale ambiguous")
    return [], warnings


def _check_high_null(df, profiles, ctx):
    warnings = []
    for col, p in profiles.items():
        if p.null_like_rate > 0.5:
            warnings.append(f"column {col} has {p.null_like_rate:.0%} missing-like values")
    return [], warnings


def _check_duplicate_columns(df, profiles, ctx):
    warnings = []
    cols = [str(c) for c in df.columns]
    series = {c: df[c].astype(object).map(lambda v: "" if is_null_like(v) else str(v).strip()).tolist() for c in cols}
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            if series[cols[i]] == series[cols[j]]:
                warnings.append(f"columns {cols[i]} and {cols[j]} are identical")
    return [], warnings


CHECKERS = [
    _check_null_unify,
    _check_ambiguous,
    _check_high_null,
    _check_duplicate_columns,
]


def run_coherence(df, profiles: dict, *, occupied: set | None = None, unify_nulls: bool = True) -> DetectionResult:
    ctx = CoherenceContext(occupied=set(occupied or set()), unify_nulls=unify_nulls)
    result = DetectionResult()
    for checker in CHECKERS:
        ch, wn = checker(df, profiles, ctx)
        result.changes.extend(ch)
        result.warnings.extend(wn)
    return result
