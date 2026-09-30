from __future__ import annotations
import pandas as pd
from core.models import is_null_like
from core.infer_types import CURRENCY_CHARS, BOOL_WORDS


def _clean_numeric(token: str, thousands: str | None, decimal: str | None) -> str:
    s = "".join(ch for ch in token if ch not in CURRENCY_CHARS)
    if thousands:
        s = s.replace(thousands, "")
    if decimal and decimal != ".":
        s = s.replace(decimal, ".")
    return s.strip()


def _cast_column(series: pd.Series, dtype: str, thousands: str | None, decimal: str | None):
    if dtype == "float64":
        cleaned = series.astype(object).map(lambda v: None if is_null_like(v) else _clean_numeric(str(v), thousands, decimal))
        return pd.to_numeric(pd.Series(cleaned, index=series.index), errors="coerce")
    if dtype == "int64":
        cleaned = series.astype(object).map(lambda v: None if is_null_like(v) else _clean_numeric(str(v), thousands, decimal))
        num = pd.to_numeric(pd.Series(cleaned, index=series.index), errors="coerce")
        if num.isna().any():
            return num
        return num.astype("int64")
    if dtype == "bool":
        def to_bool(v):
            if is_null_like(v):
                return None
            t = str(v).strip().lower()
            if t in ("true", "yes", "y", "oui", "vrai", "1"):
                return True
            if t in ("false", "no", "n", "non", "faux", "0"):
                return False
            return None
        mapped = series.astype(object).map(to_bool)
        return pd.array(mapped.tolist(), dtype="boolean")
    if dtype == "category":
        return series.astype("category")
    return series


def apply_changes(df_original: pd.DataFrame, changes: list, profiles: dict):
    df = df_original.copy()
    rows_before = len(df)
    accepted = [c for c in changes if c.status == "accepted"]
    mismatches: list[tuple] = []
    applied: dict[str, int] = {}

    cell_changes = [c for c in accepted if c.column is not None and c.row_index is not None]
    cell_changes.sort(key=lambda c: (c.row_index, str(c.column), c.kind))
    for c in cell_changes:
        cur = df.at[c.row_index, c.column]
        cur_s = "" if is_null_like(cur) else str(cur)
        before_s = "" if is_null_like(c.before) else str(c.before)
        if cur_s != before_s:
            mismatches.append((c.column, c.row_index, before_s, cur_s))
        df.at[c.row_index, c.column] = c.after
        applied[c.kind] = applied.get(c.kind, 0) + 1

    cast_changes = [c for c in accepted if c.kind == "type_cast" and c.row_index is None]
    casts: list[str] = []
    for c in cast_changes:
        col = c.column
        if col not in df.columns:
            continue
        p = profiles.get(col)
        thou = p.numeric_thousands if p else None
        dec = p.numeric_decimal if p else None
        df[col] = _cast_column(df[col], c.after, thou, dec)
        casts.append(f"{col}->{c.after}")
        applied["type_cast"] = applied.get("type_cast", 0) + 1

    losers = sorted({c.row_index for c in accepted if c.kind == "dedup" and c.column is None and c.row_index is not None})
    if losers:
        df = df.drop(index=losers, errors="ignore")
        applied["dedup"] = len(losers)

    df = df.reset_index(drop=True)
    summary = {
        "applied_by_kind": applied,
        "rows_before": rows_before,
        "rows_after": len(df),
        "casts": casts,
        "mismatches": mismatches,
    }
    return df, summary