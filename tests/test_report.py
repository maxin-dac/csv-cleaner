import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import json
import re
import pytest
from core.models import Change, ColumnProfile, new_change_id
from report.builder import build_report
from report.exporters import export_json, export_markdown, export_html, export_report


def _ch(kind, col, row, before, after, rule, conf=1.0, status="accepted"):
    c = Change(new_change_id(), kind, col, row, before, after, rule, conf)
    c.status = status
    return c


def _mini():
    profiles = {
        "a": ColumnProfile("a", "int64", 1.0, 0.0, 2, ["1", "2"], []),
        "b": ColumnProfile("b", "string", 1.0, 0.5, 2, ["x", "N/A"], ["low_cardinality"]),
    }
    changes = [
        _ch("type_cast", "a", None, "string", "int64", "cast:int64"),
        _ch("coherence_fix", "b", 1, "N/A", "", "null:unify"),
        _ch("dedup", None, 2, "k", None, "dedup:g0", status="rejected"),
    ]
    summary = {
        "applied_by_kind": {"type_cast": 1, "coherence_fix": 1},
        "rows_before": 3,
        "rows_after": 2,
        "casts": ["a->int64"],
        "mismatches": [("b", 1, "N/A", "x")],
    }
    return build_report(profiles, changes, ["w1"], True, summary)


def test_build_report_shape_and_canonical():
    r = _mini()
    assert r["schema_version"] == 1
    assert r["blocked_export"] is True
    assert r["counts_by_status"] == {"accepted": 2, "pending": 0, "rejected": 1}
    assert r["counts_by_kind"] == {"type_cast": 1, "coherence_fix": 1, "dedup": 1}
    assert r["rules_triggered"] == ["cast:int64", "dedup:g0", "null:unify"]
    assert [c["name"] for c in r["columns"]] == ["a", "b"]
    assert r["columns"][1]["changes_accepted"] == 1
    rows = [c["row_index"] for c in r["changes"]]
    assert rows == sorted(rows, key=lambda x: (-1 if x is None else x))
    assert "id" not in r["changes"][0]


def test_export_json_roundtrip():
    r = _mini()
    back = json.loads(export_json(r))
    assert back == r
    assert back["apply_summary"]["mismatches"] == [["b", "1", "N/A", "x"]]


def test_export_markdown_sections():
    md = export_markdown(_mini())
    assert "# Data Cleaning Report" in md
    assert "## Changes" in md
    assert "## Columns" in md
    assert "cast:int64" in md
    assert "blocked export: yes" in md


def test_export_html_escapes_and_static():
    r = _mini()
    r["changes"].append({
        "kind": "text_norm", "column": "b", "row_index": 0,
        "before": "<x>&\"", "after": "y", "rule": "text:surface",
        "confidence": 1.0, "status": "accepted",
    })
    h = export_html(r)
    assert "&lt;x&gt;&amp;&quot;" in h
    assert "<x>" not in h
    assert "charset=\"utf-8\"" in h
    assert "animation:none" in h
    assert "transition:none" in h
    assert "@keyframes" not in h
    assert re.search(r"animation\s*:\s*(?!none)", h) is None
    assert re.search(r"transition\s*:\s*(?!none)", h) is None


def test_export_dispatcher_and_unknown():
    r = _mini()
    assert export_report(r, "json").startswith("{")
    assert export_report(r, "markdown").startswith("#")
    assert export_report(r, "HTML").startswith("<!DOCTYPE")
    with pytest.raises(ValueError):
        export_report(r, "xml")
