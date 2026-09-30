from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import date
from core.models import Change, DetectionResult, new_change_id, is_null_like
from core.normalize_dates import (
    _parse_unambiguous,
    _split_numeric_date,
    _norm_year,
    _make_iso,
    _parse_time_part,
)


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NONNEG_NAME_RE = re.compile(r"\b(qty|quantity|count|counts|age|price|amount|total|sum|montant|quantite|quantité)\b", re.I)


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


def _column_iso_dates(series) -> list:
    parsed = []
    ambig = []
    for v in series.astype(object).tolist():
        if is_null_like(v):
            continue
        token = str(v).strip()
        iso = _parse_unambiguous(token, False)
        if iso is not None:
            parsed.append(iso)
            continue
        g = _split_numeric_date(token)
        if g is not None:
            ambig.append(g)
    g1s = [int(a[0]) for a in ambig]
    g2s = [int(a[1]) for a in ambig]
    order = None
    if any(x > 12 for x in g1s):
        order = "DMY"
    elif any(x > 12 for x in g2s):
        order = "MDY"
    if order:
        for g in ambig:
            y = _norm_year(g[2])
            if order == "DMY":
                m, d = int(g[1]), int(g[0])
            else:
                m, d = int(g[0]), int(g[1])
            hh, mn, ss = _parse_time_part(g[3])
            iso = _make_iso(y, m, d, hh, mn, ss)
            if iso is not None:
                parsed.append(iso)
    return parsed


def _check_future_dates(df, profiles, ctx):
    warnings = []
    today = date.today().isoformat()
    for col, p in profiles.items():
        if p.dtype_inferred != "datetime":
            continue
        future = [iso for iso in _column_iso_dates(df[col]) if iso[:10] > today]
        if future:
            warnings.append(f"column {col} has {len(future)} dates after {today}")
    return [], warnings


def _check_email_shape(df, profiles, ctx):
    warnings = []
    for col, p in profiles.items():
        if p.dtype_inferred not in ("string", "category"):
            continue
        values = [str(v).strip() for v in df[col].astype(object).tolist() if not is_null_like(v)]
        if not values:
            continue
        name_hit = "mail" in col.lower()
        at_share = sum(1 for v in values if "@" in v) / len(values)
        if not (name_hit or at_share > 0.5):
            continue
        bad = [v for v in values if not EMAIL_RE.match(v)]
        if bad:
            warnings.append(f"column {col} looks like email: {len(bad)} values do not match a basic email shape")
    return [], warnings


def _to_float(token, p):
    s = str(token).strip()
    if p.numeric_thousands:
        s = s.replace(p.numeric_thousands, "")
    if p.numeric_decimal and p.numeric_decimal != ".":
        s = s.replace(p.numeric_decimal, ".")
    try:
        return float(s)
    except ValueError:
        return None


def _check_negative_values(df, profiles, ctx):
    warnings = []
    for col, p in profiles.items():
        if p.dtype_inferred not in ("int64", "float64"):
            continue
        if not NONNEG_NAME_RE.search(col):
            continue
        negatives = sum(1 for v in df[col].astype(object).tolist() if not is_null_like(v) and (_to_float(v, p) or 0.0) < 0)
        if negatives:
            warnings.append(f"column {col} has {negatives} negative values although its name suggests a non-negative quantity")
    return [], warnings


CHECKERS = [
    _check_null_unify,
    _check_ambiguous,
    _check_high_null,
    _check_duplicate_columns,
    _check_future_dates,
    _check_email_shape,
    _check_negative_values,
]


def run_coherence(df, profiles: dict, *, occupied: set | None = None, unify_nulls: bool = True) -> DetectionResult:
    ctx = CoherenceContext(occupied=set(occupied or set()), unify_nulls=unify_nulls)
    result = DetectionResult()
    for checker in CHECKERS:
        ch, wn = checker(df, profiles, ctx)
        result.changes.extend(ch)
        result.warnings.extend(wn)
    return result
