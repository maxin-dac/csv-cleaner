import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd
from core.coherence import run_coherence
from core.models import ColumnProfile


def _prof(name, dtype, flags=None, null_rate=0.0):
    return ColumnProfile(name, dtype, 1.0, null_rate, 3, [], flags or [])


def test_null_unify_changes():
    df = pd.DataFrame({"n": ["N/A", "-", "", "ok"]}, dtype=object)
    profiles = {"n": _prof("n", "string")}
    dr = run_coherence(df, profiles, unify_nulls=True)
    after = {c.row_index: c.after for c in dr.changes}
    assert after == {0: "", 1: ""}
    assert all(c.rule == "null:unify" for c in dr.changes)


def test_null_unify_disabled():
    df = pd.DataFrame({"n": ["N/A"]}, dtype=object)
    profiles = {"n": _prof("n", "string")}
    dr = run_coherence(df, profiles, unify_nulls=False)
    assert dr.changes == []


def test_null_unify_respects_occupied():
    df = pd.DataFrame({"n": ["N/A"]}, dtype=object)
    profiles = {"n": _prof("n", "string")}
    dr = run_coherence(df, profiles, occupied={("n", 0)}, unify_nulls=True)
    assert dr.changes == []


def test_ambiguous_warning():
    df = pd.DataFrame({"x": ["1.234"]}, dtype=object)
    profiles = {"x": _prof("x", "string", ["numeric_locale_ambiguous"])}
    dr = run_coherence(df, profiles)
    assert any("locale ambiguous" in w for w in dr.warnings)


def test_high_null_warning():
    df = pd.DataFrame({"x": ["", ""]}, dtype=object)
    profiles = {"x": _prof("x", "string", null_rate=0.8)}
    dr = run_coherence(df, profiles)
    assert any("missing-like" in w for w in dr.warnings)


def test_duplicate_columns_warning():
    df = pd.DataFrame({"a": ["1", "2"], "b": ["1", "2"]}, dtype=object)
    profiles = {"a": _prof("a", "int64"), "b": _prof("b", "int64")}
    dr = run_coherence(df, profiles)
    assert any("identical" in w for w in dr.warnings)