from __future__ import annotations
import re
import unicodedata
from rapidfuzz import fuzz
from core.models import Change, DetectionResult, new_change_id, is_null_like


WS_RE = re.compile(r"\s+")


def _surface(token: str, case: str) -> str:
    s = unicodedata.normalize("NFKC", token)
    s = WS_RE.sub(" ", s).strip()
    if case == "lower":
        s = s.lower()
    elif case == "upper":
        s = s.upper()
    elif case == "title":
        s = s.title()
    return s


def _uf_parent(parent: list[int], x: int) -> int:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _uf_union(parent: list[int], a: int, b: int) -> None:
    ra, rb = _uf_parent(parent, a), _uf_parent(parent, b)
    if ra != rb:
        parent[rb] = ra


def _cluster_values(values: list[str], threshold: int) -> list[list[int]]:
    n = len(values)
    parent = list(range(n))
    low = [v.lower() for v in values]
    for i in range(n):
        for j in range(i + 1, n):
            if fuzz.token_set_ratio(low[i], low[j]) >= threshold:
                _uf_union(parent, i, j)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(_uf_parent(parent, i), []).append(i)
    return list(groups.values())


def normalize_text_column(series, name: str, dtype: str, *, case: str = "keep", cat_threshold: int = 90):
    raw = series.astype(object).tolist()
    changes: list[Change] = []
    warnings: list[str] = []
    cleaned: dict[int, str] = {}
    for i, v in enumerate(raw):
        if is_null_like(v):
            continue
        original = str(v)
        c = _surface(original, case)
        cleaned[i] = c
        if c != original:
            changes.append(Change(new_change_id(), "text_norm", name, i, original, c, "text:surface", 1.0))
    if dtype == "category" and cleaned:
        distinct = sorted(set(cleaned.values()))
        clusters = _cluster_values(distinct, cat_threshold)
        canon: dict[str, str] = {}
        for cl in clusters:
            members = [distinct[k] for k in cl]
            if len(members) == 1:
                canon[members[0]] = members[0]
                continue
            freq: dict[str, int] = {}
            first: dict[str, int] = {}
            for i in sorted(cleaned):
                val = cleaned[i]
                if val in members:
                    freq[val] = freq.get(val, 0) + 1
                    first.setdefault(val, i)
            winner = max(members, key=lambda m: (freq.get(m, 0), -first.get(m, 10**9)))
            for m in members:
                canon[m] = winner
            warnings.append(f"merged category variants in {name}: {members} -> {winner}")
        by_cell = {c.row_index: c for c in changes if c.kind == "text_norm"}
        final: list[Change] = []
        for i in sorted(cleaned):
            original = str(raw[i])
            surf = cleaned[i]
            win = canon.get(surf, surf)
            if win != original:
                if win != surf:
                    conf = fuzz.token_set_ratio(surf.lower(), win.lower()) / 100.0
                    final.append(Change(new_change_id(), "cat_merge", name, i, original, win, "text:cat_merge", conf))
                else:
                    final.append(by_cell[i])
            elif i in by_cell:
                final.append(by_cell[i])
        changes = final
    return changes, warnings


def normalize_text(df, profiles: dict, *, case: str = "keep", cat_threshold: int = 90) -> DetectionResult:
    result = DetectionResult()
    for col, p in profiles.items():
        if p.dtype_inferred in ("string", "category"):
            ch, wn = normalize_text_column(df[col], col, p.dtype_inferred, case=case, cat_threshold=cat_threshold)
            result.changes.extend(ch)
            result.warnings.extend(wn)
    return result