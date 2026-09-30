import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import copy
import pandas as pd
from core.apply import apply_changes
from core.models import Change, new_change_id
from core.proposals import aggregate


def _ch(kind, col, row, before, after, conf=1.0):
    return Change(new_change_id(), kind, col, row, before, after, f"r:{kind}", conf)


def test_reject_all_preserves_original():
    df = pd.DataFrame({"a": [" x ", "y"], "b": ["1", "2"]}, dtype=object)
    changes = [_ch("text_norm", "a", 0, " x ", "x")]
    for c in changes:
        c.status = "rejected"
    clean, summ = apply_changes(df, changes, {})
    assert clean.reset_index(drop=True).equals(df.reset_index(drop=True))
    assert summ["rows_before"] == summ["rows_after"]


def test_original_never_mutated():
    df = pd.DataFrame({"a": [" x ", "y"]}, dtype=object)
    snapshot = copy.deepcopy(df)
    changes = [_ch("text_norm", "a", 0, " x ", "x")]
    changes[0].status = "accepted"
    apply_changes(df, changes, {})
    assert df.equals(snapshot)


def test_deterministic_double_apply():
    df = pd.DataFrame({"a": [" x ", "y"], "b": ["1", "2"]}, dtype=object)
    changes = [_ch("text_norm", "a", 0, " x ", "x")]
    changes[0].status = "accepted"
    c1, _ = apply_changes(df, changes, {})
    c2, _ = apply_changes(df, changes, {})
    assert c1.equals(c2)


def test_dedup_row_count_invariant():
    df = pd.DataFrame({"k": ["a", "a", "b"]}, dtype=object)
    changes = [_ch("dedup", None, 1, "a", None)]
    changes[0].status = "accepted"
    clean, summ = apply_changes(df, changes, {})
    assert summ["rows_after"] == summ["rows_before"] - 1
    assert len(clean) == 2
    assert list(clean["k"]) == ["a", "b"]


def test_untouched_column_equal_original():
    df = pd.DataFrame({"a": [" x "], "b": ["keep"]}, dtype=object)
    changes = [_ch("text_norm", "a", 0, " x ", "x")]
    changes[0].status = "accepted"
    clean, _ = apply_changes(df, changes, {})
    assert list(clean["b"]) == list(df["b"])


def test_pipeline_no_dupes_preserves_rows():
    df = pd.DataFrame({"a": ["1", "2"], "b": ["x", "y"]}, dtype=object)
    profiles, dr = aggregate(df, unify_nulls=True)
    for c in dr.changes:
        c.status = "accepted"
    clean, summ = apply_changes(df, dr.changes, profiles)
    assert summ["rows_after"] == 2