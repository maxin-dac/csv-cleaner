import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd
from core.normalize_dates import normalize_date_column


def _s(values, name="d"):
    return pd.Series(values, name=name, dtype=object)


def _after(changes):
    return [c.after for c in changes]


def test_dmy_resolved_by_column_vote():
    ch, wn, bl = normalize_date_column(_s(["01/02/2024", "13/05/2024"]), "d")
    assert _after(ch) == ["2024-02-01", "2024-05-13"]
    assert bl is False
    assert not any("ambiguous" in w for w in wn)


def test_mdy_resolved_by_column_vote():
    ch, wn, bl = normalize_date_column(_s(["02/13/2024", "01/05/2024"]), "d")
    assert _after(ch) == ["2024-02-13", "2024-01-05"]


def test_ambiguous_left_unchanged_and_blocks():
    ch, wn, bl = normalize_date_column(_s(["01/02/2024", "03/04/2024"]), "d")
    assert ch == []
    assert bl is True
    assert any("ambiguous" in w for w in wn)


def test_month_name_english():
    ch, wn, bl = normalize_date_column(_s(["12 Jan 2024"]), "d")
    assert _after(ch) == ["2024-01-12"]


def test_month_name_french():
    ch, wn, bl = normalize_date_column(_s(["5 mars 2024"]), "d")
    assert _after(ch) == ["2024-03-05"]


def test_iso_passthrough_no_change():
    ch, wn, bl = normalize_date_column(_s(["2024-01-02"]), "d")
    assert ch == []
    assert bl is False


def test_unparseable_only_no_block():
    ch, wn, bl = normalize_date_column(_s(["hello", "world"]), "d")
    assert ch == []
    assert bl is False
    assert any("no recognizable" in w for w in wn)


def test_partial_failure_blocks():
    ch, wn, bl = normalize_date_column(_s(["2024-01-02", "garbage", "garbage"]), "d")
    assert bl is True
    assert any("unparsed" in w for w in wn)


def test_epoch_when_allowed():
    ch, wn, bl = normalize_date_column(_s(["1704067200"]), "d", allow_epoch_excel=True)
    assert _after(ch) == ["2024-01-01"]


def test_excel_serial_when_allowed():
    ch, wn, bl = normalize_date_column(_s(["45292"]), "d", allow_epoch_excel=True)
    assert _after(ch) == ["2024-01-01"]


def test_epoch_disabled_by_default():
    ch, wn, bl = normalize_date_column(_s(["1704067200"]), "d")
    assert ch == []