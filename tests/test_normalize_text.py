import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd
from core.normalize_text import normalize_text_column, normalize_text
from core.models import ColumnProfile


def _s(values, name="c"):
    return pd.Series(values, name=name, dtype=object)


def _after(changes):
    return {c.row_index: c.after for c in changes}


def test_surface_trim_and_collapse():
    ch, wn = normalize_text_column(_s(["  a  b ", "c"]), "c", "string")
    assert _after(ch) == {0: "a b"}
    assert ch[0].rule == "text:surface"


def test_surface_nfkc_fullwidth():
    ch, wn = normalize_text_column(_s(["ＦＵＬＬＷＩＤＴＨ"]), "c", "string")
    assert _after(ch) == {0: "FULLWIDTH"}


def test_surface_case_lower():
    ch, wn = normalize_text_column(_s(["Ab", "CD"]), "c", "string", case="lower")
    assert _after(ch) == {0: "ab", 1: "cd"}


def test_null_like_skipped():
    ch, wn = normalize_text_column(_s(["", "N/A", "x"]), "c", "string")
    assert _after(ch) == {}


def test_cat_merge_cluster_and_canonical():
    ch, wn = normalize_text_column(_s(["New", "new", "NEW", "Used"]), "c", "category", cat_threshold=90)
    after = _after(ch)
    assert after.get(1) == "New"
    assert after.get(2) == "New"
    assert 0 not in after
    assert 3 not in after
    rules = {c.row_index: c.rule for c in ch}
    assert rules[1] == "text:cat_merge"
    assert any("merged category" in w for w in wn)


def test_cat_merge_keeps_surface_only_when_no_cluster():
    ch, wn = normalize_text_column(_s(["  Alpha  ", "Beta"]), "c", "category", cat_threshold=90)
    after = _after(ch)
    assert after.get(0) == "Alpha"
    assert 1 not in after


def test_normalize_text_dispatch_by_dtype():
    df = pd.DataFrame({"a": ["  x  "], "b": ["1"]}, dtype=object)
    profiles = {
        "a": ColumnProfile("a", "string", 1.0, 0.0, 1, ["x"], []),
        "b": ColumnProfile("b", "int64", 1.0, 0.0, 1, ["1"], []),
    }
    dr = normalize_text(df, profiles)
    cols = {c.column for c in dr.changes}
    assert cols == {"a"}