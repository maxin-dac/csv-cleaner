from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone
from core.models import Change, DetectionResult, new_change_id, is_null_like


MONTHS = {
    "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
    "january":1,"february":2,"march":3,"april":4,"june":6,"july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "janv":1,"janvier":1,"fevr":2,"février":2,"mars":3,"avr":4,"avril":4,"mai":5,"juin":6,"juil":7,"juillet":7,
    "août":8,"aout":8,"sept":9,"septembre":9,"oct":10,"octobre":10,"nov":11,"novembre":11,"déc":12,"decembre":12,
}

ISO_DASH = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?$")
ISO_SLASH = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?$")
MON1 = re.compile(r"^(\d{1,2})[\s-]+([A-Za-zÀ-ÿ]{3,})\.?[\s-]+(\d{2,4})(?:[\s,]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$")
MON2 = re.compile(r"^([A-Za-zÀ-ÿ]{3,})\.?[\s-]+(\d{1,2}),?[\s-]+(\d{2,4})(?:[\s,]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$")
SPLIT_RE = re.compile(r"^(\d{1,2})([/.\-])(\d{1,2})\2(\d{2,4})(?:[ T](\d{1,2}:\d{2}(?::\d{2})?))?$")
EPOCH_RE = re.compile(r"^\d{9,15}$")
EXCEL_RE = re.compile(r"^\d{1,7}(?:\.\d+)?$")


def _month_token_to_int(token: str):
    return MONTHS.get(token.lower().replace(".", "").strip())


def _norm_year(token: str) -> int:
    y = int(token)
    if y < 100:
        y = 2000 + y if y < 70 else 1900 + y
    return y


def _parse_time_part(tp):
    if not tp:
        return (0, 0, 0)
    parts = tp.split(":")
    while len(parts) < 3:
        parts.append("0")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def _make_iso(y, m, d, hh, mn, ss):
    try:
        datetime(y, m, d, hh, mn, ss)
    except Exception:
        return None
    if hh or mn or ss:
        return f"{y:04d}-{m:02d}-{d:02d} {hh:02d}:{mn:02d}:{ss:02d}"
    return f"{y:04d}-{m:02d}-{d:02d}"


def _time_from_groups(g4, g5, g6):
    hh = int(g4) if g4 else 0
    mn = int(g5) if g5 else 0
    ss = int(g6) if g6 else 0
    return (hh, mn, ss)


def _parse_unambiguous(token: str, allow_epoch_excel: bool):
    m = ISO_DASH.match(token)
    if m:
        hh, mn, ss = _time_from_groups(m.group(4), m.group(5), m.group(6))
        return _make_iso(int(m.group(1)), int(m.group(2)), int(m.group(3)), hh, mn, ss)
    m = ISO_SLASH.match(token)
    if m:
        hh, mn, ss = _time_from_groups(m.group(4), m.group(5), m.group(6))
        return _make_iso(int(m.group(1)), int(m.group(2)), int(m.group(3)), hh, mn, ss)
    m = MON1.match(token)
    if m:
        mo = _month_token_to_int(m.group(2))
        if mo:
            hh, mn, ss = _time_from_groups(m.group(4), m.group(5), m.group(6))
            return _make_iso(_norm_year(m.group(3)), mo, int(m.group(1)), hh, mn, ss)
    m = MON2.match(token)
    if m:
        mo = _month_token_to_int(m.group(1))
        if mo:
            hh, mn, ss = _time_from_groups(m.group(4), m.group(5), m.group(6))
            return _make_iso(_norm_year(m.group(3)), mo, int(m.group(2)), hh, mn, ss)
    if allow_epoch_excel:
        if EPOCH_RE.match(token):
            ts = int(token)
            ln = len(token)
            sec = ts if ln <= 10 else (ts / 1000 if ln <= 13 else ts / 1000000)
            try:
                dt = datetime.fromtimestamp(sec, timezone.utc)
            except Exception:
                return None
            return _make_iso(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        if EXCEL_RE.match(token):
            val = float(token)
            if 1 <= val <= 2958465:
                dt = datetime(1899, 12, 30, tzinfo=timezone.utc) + timedelta(days=val)
                return _make_iso(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    return None


def _split_numeric_date(token: str):
    m = SPLIT_RE.match(token)
    if not m:
        return None
    return (m.group(1), m.group(3), m.group(4), m.group(5))


def normalize_date_column(series, name: str, *, allow_epoch_excel: bool = False, fail_rate: float = 0.05, ambig_blocks: bool = True):
    raw = series.astype(object).tolist()
    nonnull_idx = [i for i, v in enumerate(raw) if not is_null_like(v)]
    tokens = {i: str(raw[i]).strip() for i in nonnull_idx}
    changes: list[Change] = []
    resolved_iso: dict[int, str] = {}
    ambiguous_groups: list[tuple] = []
    resolved = 0
    fail = 0
    ambig = 0
    for i in nonnull_idx:
        t = tokens[i]
        res = _parse_unambiguous(t, allow_epoch_excel)
        if res is not None:
            resolved_iso[i] = res
            resolved += 1
            continue
        grp = _split_numeric_date(t)
        if grp is not None:
            ambiguous_groups.append((i,) + grp)
            continue
        fail += 1
    if ambiguous_groups:
        g1s = [int(a[1]) for a in ambiguous_groups]
        g2s = [int(a[2]) for a in ambiguous_groups]
        order = None
        if any(x > 12 for x in g1s):
            order = "DMY"
        elif any(x > 12 for x in g2s):
            order = "MDY"
        if order is None:
            ambig = len(ambiguous_groups)
        else:
            for a in ambiguous_groups:
                i, g1, g2, g3, tp = a
                y = _norm_year(g3)
                if order == "DMY":
                    m, d = int(g2), int(g1)
                else:
                    m, d = int(g1), int(g2)
                hh, mn, ss = _parse_time_part(tp)
                iso = _make_iso(y, m, d, hh, mn, ss)
                if iso is None:
                    fail += 1
                else:
                    resolved_iso[i] = iso
                    resolved += 1
    for i, iso in resolved_iso.items():
        before = tokens[i]
        if iso != before:
            changes.append(Change(new_change_id(), "date_norm", name, i, before, iso, "date:iso", 1.0))
    warnings: list[str] = []
    total_nn = len(nonnull_idx)
    if fail:
        warnings.append(f"{fail} unparsed date values in column {name}")
    if ambig:
        warnings.append(f"{ambig} ambiguous DMY/MDY dates left unchanged in column {name}")
    if resolved == 0 and ambig == 0 and total_nn > 0:
        warnings.append(f"no recognizable dates in column {name}")
    blocked = False
    if total_nn > 0:
        if resolved > 0 and fail / total_nn > fail_rate:
            blocked = True
        if ambig > 0 and ambig_blocks:
            blocked = True
    return changes, warnings, blocked


def normalize_dates(df, profiles: dict, *, allow_epoch_excel: bool = False, fail_rate: float = 0.05, ambig_blocks: bool = True) -> DetectionResult:
    result = DetectionResult()
    for col, p in profiles.items():
        if p.dtype_inferred == "datetime":
            ch, wn, bl = normalize_date_column(df[col], col, allow_epoch_excel=allow_epoch_excel, fail_rate=fail_rate, ambig_blocks=ambig_blocks)
            result.changes.extend(ch)
            result.warnings.extend(wn)
            result.blocked_export = result.blocked_export or bl
    return result