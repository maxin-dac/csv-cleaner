from __future__ import annotations


SCHEMA_VERSION = 1


def _s(value):
    return "" if value is None else str(value)


def _change_sort_key(c):
    return (
        -1 if c["row_index"] is None else c["row_index"],
        _s(c["column"]),
        _s(c["kind"]),
        _s(c["rule"]),
        _s(c["before"]),
        _s(c["after"]),
    )


def _round(value):
    try:
        return round(float(value), 4)
    except Exception:
        return value


def build_report(profiles, changes, warnings, blocked_export, apply_summary):
    accepted_by_col = {}
    counts_by_kind = {}
    counts_by_status = {"accepted": 0, "pending": 0, "rejected": 0}
    rules = set()
    canonical = []
    for c in changes:
        counts_by_kind[c.kind] = counts_by_kind.get(c.kind, 0) + 1
        counts_by_status[c.status] = counts_by_status.get(c.status, 0) + 1
        rules.add(_s(c.rule))
        if c.status == "accepted" and c.column is not None:
            accepted_by_col[c.column] = accepted_by_col.get(c.column, 0) + 1
        canonical.append({
            "kind": _s(c.kind),
            "column": c.column,
            "row_index": c.row_index,
            "before": c.before,
            "after": c.after,
            "rule": _s(c.rule),
            "confidence": _round(c.confidence),
            "status": _s(c.status),
        })
    canonical.sort(key=_change_sort_key)

    columns = []
    for name in sorted(profiles.keys()):
        p = profiles[name]
        columns.append({
            "name": _s(name),
            "dtype": _s(p.dtype_inferred),
            "confidence": _round(p.confidence),
            "null_like_rate": _round(p.null_like_rate),
            "distinct": int(p.distinct),
            "flags": sorted(_s(f) for f in p.flags),
            "numeric_thousands": p.numeric_thousands,
            "numeric_decimal": p.numeric_decimal,
            "changes_accepted": accepted_by_col.get(name, 0),
        })

    summary = {
        "applied_by_kind": { _s(k): int(v) for k, v in apply_summary.get("applied_by_kind", {}).items() },
        "rows_before": int(apply_summary.get("rows_before", 0)),
        "rows_after": int(apply_summary.get("rows_after", 0)),
        "casts": sorted(_s(x) for x in apply_summary.get("casts", [])),
        "mismatches": [ [_s(x) for x in m] for m in apply_summary.get("mismatches", []) ],
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "blocked_export": bool(blocked_export),
        "warnings": sorted(_s(w) for w in warnings),
        "counts_by_kind": counts_by_kind,
        "counts_by_status": counts_by_status,
        "rules_triggered": sorted(rules),
        "columns": columns,
        "changes": canonical,
        "apply_summary": summary,
    }
