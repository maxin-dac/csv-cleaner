import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pandas as pd
from core.duplicates import find_duplicates


def test_groups_and_losers():
    df = pd.DataFrame({
        "name": ["John Doe", "john  doe", "Jane Smith", "JOHN DOE"],
        "city": ["Paris", "Paris", "Lyon", "Paris"],
    }, dtype=object)
    dr = find_duplicates(df, ["name", "city"], threshold=85)
    losers = sorted(c.row_index for c in dr.changes)
    assert losers == [1, 3]
    assert all(c.column is None for c in dr.changes)
    assert all(c.kind == "dedup" for c in dr.changes)
    assert all(c.after is None for c in dr.changes)


def test_no_duplicates_empty():
    df = pd.DataFrame({"name": ["Alice", "Bob", "Carol"]}, dtype=object)
    dr = find_duplicates(df, ["name"], threshold=90)
    assert dr.changes == []


def test_unknown_key_column_warns():
    df = pd.DataFrame({"name": ["a", "a"]}, dtype=object)
    dr = find_duplicates(df, ["missing"], threshold=85)
    assert dr.changes == []
    assert any("unknown columns" in w for w in dr.warnings)


def test_completeness_picks_winner():
    df = pd.DataFrame({
        "name": ["John Doe", "john doe"],
        "email": ["", "j@x.com"],
    }, dtype=object)
    dr = find_duplicates(df, ["name"], threshold=85)
    losers = [c.row_index for c in dr.changes]
    assert losers == [0]