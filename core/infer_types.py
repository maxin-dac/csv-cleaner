from __future__ import annotations
import re
import pandas as pd
from core.models import ColumnProfile, Change, new_change_id, is_null_like


BOOL_WORDS = {"true","false","yes","no","y","n","oui","non","vrai","faux"}
CURRENCY_CHARS = "$€£¥\u00a0 \t"
CARD_MAX = 50
CARD_RATIO = 0.5

INT_RE = re.compile(r"^[+-]?\d+$")
LEAD_RE = re.compile(r"^[+-]?0\d+$")
FLOAT_LIT = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
LOOSE_NUM_RE = re.compile(r"^[+-]?\d{1,3}(?:[ .,]\d{3})*(?:[.,]\d+)?$")
NUM_DATE = r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?"
MON_DATE1 = r"\d{1,2}[\s-]+[A-Za-zÀ-ÿ]{3,}\.?\s+\d{2,4}(?:[\s,]+\d{1,2}:\d{2}(?::\d{2})?)?"
MON_DATE2 = r"[A-Za-zÀ-ÿ]{3,}\.?\s+\d{1,2},?\s+\d{2,4}(?:[\s,]+\d{1,2}:\d{2}(?::\d{2})?)?"
DATEISH_RE = re.compile(r"^(?:" + NUM_DATE + r"|" + MON_DATE1 + r"|" + MON_DATE2 + r")$")


def _strip_currency(token: str) -> str:
    return "".join(c for c in token if c not in CURRENCY_CHARS)


def _is_float_literal(token: str) -> bool:
    if not FLOAT_LIT.match(token):
        return False
    try:
        float(token)
        return True
    except Exception:
        return False


def _first_unique(values: list[str], k: int) -> list[str]:
    seen = set()
    out = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
            if len(out) >= k:
                break
    return out


def _try_float(tokens: list[str]):
    sep_tokens = [t for t in tokens if "." in t or "," in t]
    evidences = set()
    for t in sep_tokens:
        idx = max(t.rfind("."), t.rfind(","))
        if idx == -1:
            continue
        sep = t[idx]
        frac = t[idx + 1:]
        if frac.isdigit() and 1 <= len(frac) <= 2:
            evidences.add(sep)
    if len(evidences) > 1:
        return (0.0, None, None, False, "ambiguous")
    if len(evidences) == 1:
        decimal_char = evidences.pop()
    elif sep_tokens:
        return (0.0, None, None, False, "ambiguous")
    else:
        decimal_char = None
    thousands_char = None
    if decimal_char is not None:
        other = "," if decimal_char == "." else "."
        if any(other in t for t in sep_tokens):
            thousands_char = other
    success = 0
    needed_strip = False
    for t in tokens:
        cleaned = _strip_currency(t)
        if cleaned != t:
            needed_strip = True
        if thousands_char:
            cleaned = cleaned.replace(thousands_char, "")
        if decimal_char and decimal_char != ".":
            cleaned = cleaned.replace(decimal_char, ".")
        if _is_float_literal(cleaned):
            success += 1
    rate = success / len(tokens) if tokens else 0.0
    return (rate, decimal_char, thousands_char, needed_strip, "ok")


def infer_column(series: pd.Series, threshold: float = 0.95, max_sample: int = 50000) -> ColumnProfile:
    name = str(series.name) if series.name is not None else ""
    raw = series.astype(object).tolist()
    total = len(raw)
    null_count = sum(1 for v in raw if is_null_like(v))
    null_like_rate = null_count / total if total else 0.0
    vals_raw = [str(v).strip() for v in raw if not is_null_like(v)]
    distinct = len(set(vals_raw))
    samples = _first_unique(vals_raw, 5)
    flags: list[str] = []
    work = vals_raw
    if len(work) > max_sample:
        work = work[:max_sample]
        flags.append("sampled")
    if not work:
        return ColumnProfile(name, "string", 0.0, null_like_rate, distinct, samples, flags + ["all_null"], None, None)
    n = len(work)
    bool_ok = sum(1 for t in work if t.lower() in BOOL_WORDS)
    if bool_ok / n >= threshold:
        return ColumnProfile(name, "bool", bool_ok / n, null_like_rate, distinct, samples, flags, None, None)
    int_ok = sum(1 for t in work if INT_RE.match(t))
    if int_ok / n >= threshold:
        leading = any(LEAD_RE.match(t) for t in work if INT_RE.match(t))
        if leading:
            return ColumnProfile(name, "string", int_ok / n, null_like_rate, distinct, samples, flags + ["leading_zeros_kept_as_string"], None, None)
        return ColumnProfile(name, "int64", int_ok / n, null_like_rate, distinct, samples, flags, None, None)
    rate, dec, thou, strip, status = _try_float(work)
    if status == "ambiguous":
        loose = sum(1 for t in work if LOOSE_NUM_RE.match(_strip_currency(t)))
        return ColumnProfile(name, "string", loose / n, null_like_rate, distinct, samples, flags + ["numeric_locale_ambiguous"], None, None)
    if rate >= threshold:
        f2 = list(flags)
        if strip:
            f2.append("currency_or_spaces_stripped")
        return ColumnProfile(name, "float64", rate, null_like_rate, distinct, samples, f2, thou, dec)
    dt_ok = sum(1 for t in work if DATEISH_RE.match(t))
    if dt_ok / n >= threshold:
        return ColumnProfile(name, "datetime", dt_ok / n, null_like_rate, distinct, samples, flags, None, None)
    if distinct <= CARD_MAX and distinct / n <= CARD_RATIO:
        return ColumnProfile(name, "category", 1.0, null_like_rate, distinct, samples, flags + ["low_cardinality"], None, None)
    return ColumnProfile(name, "string", 1.0, null_like_rate, distinct, samples, flags, None, None)


def infer_types(df: pd.DataFrame, threshold: float = 0.95, max_sample: int = 50000) -> dict[str, ColumnProfile]:
    return {str(col): infer_column(df[col], threshold=threshold, max_sample=max_sample) for col in df.columns}


def build_type_changes(profiles: dict[str, ColumnProfile]) -> list[Change]:
    castable = {"int64", "float64", "bool", "category"}
    changes = []
    for name, p in profiles.items():
        if p.dtype_inferred in castable:
            changes.append(Change(new_change_id(), "type_cast", name, None, "string", p.dtype_inferred, f"cast:{p.dtype_inferred}", p.confidence))
    return changes