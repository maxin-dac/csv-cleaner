from __future__ import annotations
import re
from rapidfuzz import fuzz
from core.models import Change, DetectionResult, new_change_id, is_null_like


PUNCT_RE = re.compile(r"[^\w\s]")
WS_RE = re.compile(r"\s+")
DEFAULT_MAX_BUCKET = 1500


def _norm_key(row_values: list) -> str:
    parts = []
    for v in row_values:
        if is_null_like(v):
            parts.append("")
            continue
        s = str(v).lower()
        s = PUNCT_RE.sub(" ", s)
        s = WS_RE.sub(" ", s).strip()
        parts.append(s)
    return "\x1f".join(parts)


def _completeness(row_values: list) -> int:
    return sum(1 for v in row_values if not is_null_like(v))


def _uf_parent(parent: list[int], x: int) -> int:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _uf_union(parent: list[int], a: int, b: int) -> None:
    ra, rb = _uf_parent(parent, a), _uf_parent(parent, b)
    if ra != rb:
        parent[rb] = ra


def find_duplicates(df, key_columns: list[str], *, threshold: int = 85, max_bucket: int = DEFAULT_MAX_BUCKET) -> DetectionResult:
    result = DetectionResult()
    cols = [str(c) for c in key_columns]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        result.warnings.append(f"duplicate keys reference unknown columns: {missing}")
        return result
    key_rows = df[cols].astype(object).values.tolist()
    all_rows = df.astype(object).values.tolist()
    keys = [_norm_key(r) for r in key_rows]
    buckets: dict[str, list[int]] = {}
    for i, k in enumerate(keys):
        sig = k[0] if k else ""
        buckets.setdefault(sig, []).append(i)
    gid = 0
    for sig, members in buckets.items():
        if len(members) < 2:
            continue
        if len(members) > max_bucket:
            result.warnings.append(f"block '{sig}' has {len(members)} rows, truncated to {max_bucket} (possible missed duplicates)")
            members = members[:max_bucket]
        parent = list(range(len(members)))
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                ia, ib = members[a], members[b]
                if fuzz.token_set_ratio(keys[ia], keys[ib]) >= threshold:
                    _uf_union(parent, a, b)
        groups: dict[int, list[int]] = {}
        for a in range(len(members)):
            groups.setdefault(_uf_parent(parent, a), []).append(members[a])
        for _, gidx in groups.items():
            if len(gidx) < 2:
                continue
            winner = max(gidx, key=lambda i: (_completeness(all_rows[i]), -i))
            for i in gidx:
                if i == winner:
                    continue
                conf = fuzz.token_set_ratio(keys[i], keys[winner]) / 100.0
                result.changes.append(Change(new_change_id(), "dedup", None, i, keys[i], None, f"dedup:g{gid}", conf))
            gid += 1
    if result.changes:
        result.warnings.append(f"{gid} approximate duplicate groups detected on {cols}")
    return result
