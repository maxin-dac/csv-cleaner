import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import json
import pandas as pd
from core.proposals import aggregate
from core.apply import apply_changes
from report.builder import build_report
from report.exporters import export_json


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _ck(c):
    return (
        -1 if c["row_index"] is None else c["row_index"],
        "" if c["column"] is None else str(c["column"]),
        str(c["kind"]),
        str(c["rule"]),
        "" if c["before"] is None else str(c["before"]),
        "" if c["after"] is None else str(c["after"]),
    )


def _normalize(rep):
    rep = json.loads(json.dumps(rep))
    rep["changes"] = sorted(rep["changes"], key=_ck)
    rep["columns"] = sorted(rep["columns"], key=lambda c: c["name"])
    rep["warnings"] = sorted(rep["warnings"])
    return rep


def test_golden_types_and_dates():
    df = pd.read_csv(ROOT / "data" / "golden" / "messy_in.csv", dtype=str, keep_default_na=False)
    profiles, dr = aggregate(df, unify_nulls=True)
    date_counts = {}
    for ch in dr.changes:
        if ch.kind == "date_norm":
            date_counts[ch.column] = date_counts.get(ch.column, 0) + 1
    actual = {}
    for col, p in profiles.items():
        actual[col] = {
            "dtype": p.dtype_inferred,
            "flags": sorted(p.flags),
            "date_changes": date_counts.get(col, 0),
            "numeric_thousands": p.numeric_thousands,
            "numeric_decimal": p.numeric_decimal,
        }
    expected = json.loads((ROOT / "data" / "golden" / "types_dates_expected.json").read_text())
    assert actual == expected


def test_golden_clean_output():
    df = pd.read_csv(ROOT / "data" / "golden" / "messy_in.csv", dtype=str, keep_default_na=False)
    profiles, dr = aggregate(df, unify_nulls=True)
    for c in dr.changes:
        c.status = "accepted"
    clean, summ = apply_changes(df, dr.changes, profiles)
    got = clean.to_csv(index=False, lineterminator="\n")
    exp = (ROOT / "data" / "golden" / "messy_out_expected.csv").read_text()
    assert got.splitlines() == exp.splitlines()
    assert summ["rows_after"] == summ["rows_before"]


def test_golden_report():
    df = pd.read_csv(ROOT / "data" / "golden" / "messy_in.csv", dtype=str, keep_default_na=False)
    profiles, dr = aggregate(df, unify_nulls=True)
    for c in dr.changes:
        c.status = "accepted"
    clean, summ = apply_changes(df, dr.changes, profiles)
    report = build_report(profiles, dr.changes, dr.warnings, dr.blocked_export, summ)
    got = _normalize(json.loads(export_json(report)))
    exp = _normalize(json.loads((ROOT / "data" / "golden" / "messy_report_expected.json").read_text()))
    assert got == exp