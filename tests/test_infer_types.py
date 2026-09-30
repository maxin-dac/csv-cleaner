import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd
from core.models import Change, ColumnProfile, DetectionResult, is_null_like, new_change_id
from core.infer_types import build_type_changes, infer_column, infer_types


def _s(values, name="c"):
    return pd.Series(values, name=name, dtype=object)


def test_is_null_like_tokens():
    assert is_null_like(None)
    assert is_null_like("")
    assert is_null_like("N/A")
    assert is_null_like("-")
    assert not is_null_like("0")
    assert not is_null_like("7")


def test_plain_int():
    p = infer_column(_s(["3", "7", "12"]))
    assert p.dtype_inferred == "int64"
    assert p.confidence == 1.0
    assert p.numeric_thousands is None


def test_leading_zeros_stay_string():
    p = infer_column(_s(["001", "002", "003"]))
    assert p.dtype_inferred == "string"
    assert "leading_zeros_kept_as_string" in p.flags


def test_float_us_locale():
    p = infer_column(_s(["1,234.56", "2,100.00", "99.90"]))
    assert p.dtype_inferred == "float64"
    assert p.numeric_decimal == "."
    assert p.numeric_thousands == ","


def test_float_eu_locale():
    p = infer_column(_s(["1.234,56", "2.100,00", "99,90"]))
    assert p.dtype_inferred == "float64"
    assert p.numeric_decimal == ","
    assert p.numeric_thousands == "."


def test_float_ambiguous_locale_is_string():
    p = infer_column(_s(["1.234", "5.678"]))
    assert p.dtype_inferred == "string"
    assert "numeric_locale_ambiguous" in p.flags


def test_float_currency_stripped():
    p = infer_column(_s(["$1,234.56", "$99.90"]))
    assert p.dtype_inferred == "float64"
    assert "currency_or_spaces_stripped" in p.flags


def test_bool_words():
    p = infer_column(_s(["true", "false", "oui"]))
    assert p.dtype_inferred == "bool"


def test_zero_one_is_int_not_bool():
    p = infer_column(_s(["1", "0", "1"]))
    assert p.dtype_inferred == "int64"


def test_datetime_detection_no_conversion():
    p = infer_column(_s(["01/02/2024", "13/05/2024"]))
    assert p.dtype_inferred == "datetime"


def test_low_cardinality_category():
    p = infer_column(_s(["new", "new", "sent", "sent", "sent", "paid"]))
    assert p.dtype_inferred == "category"
    assert "low_cardinality" in p.flags


def test_all_null_column():
    p = infer_column(_s(["", "N/A", None, "-"]))
    assert p.dtype_inferred == "string"
    assert "all_null" in p.flags
    assert p.null_like_rate == 1.0


def test_build_type_changes_skips_string_and_datetime():
    df = pd.DataFrame({"q": ["1", "2"], "t": ["a", "b"], "d": ["01/02/2024", "03/04/2024"], "z": ["001", "002"]}, dtype=object)
    profiles = infer_types(df)
    changes = build_type_changes(profiles)
    cols = {c.column for c in changes}
    assert "q" in cols
    assert "t" not in cols
    assert "d" not in cols
    assert "z" not in cols
    assert all(c.kind == "type_cast" for c in changes)


def test_change_defaults_and_detection_extend():
    c = Change(new_change_id(), "x", "col", 0, "a", "b", "r", 1.0)
    assert c.status == "pending"
    assert c.accepted is False
    c.status = "accepted"
    assert c.accepted is True
    r1 = DetectionResult(warnings=["w1"], blocked_export=False)
    r2 = DetectionResult(changes=[c], blocked_export=True)
    r1.extend(r2)
    assert r1.blocked_export is True
    assert len(r1.changes) == 1
    assert r1.warnings == ["w1"]