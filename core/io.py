from __future__ import annotations
import csv
import io
import pandas as pd


ENCODINGS = ["utf-8", "cp1252", "latin-1"]
UTF8_BOM = b"\xef\xbb\xbf"


def detect_encoding(data: bytes) -> str:
    if data.startswith(UTF8_BOM):
        return "utf-8-sig"
    for enc in ENCODINGS:
        try:
            data.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def sniff_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def read_csv_bytes(data: bytes, max_rows: int | None = None):
    enc = detect_encoding(data)
    text = data.decode(enc)
    delim = sniff_delimiter(text[:8192])
    df = pd.read_csv(io.StringIO(text), sep=delim, dtype=str, keep_default_na=False, engine="python")
    truncated = False
    if max_rows is not None and len(df) > max_rows:
        df = df.iloc[:max_rows].copy()
        truncated = True
    df.columns = [str(c) for c in df.columns]
    return df, truncated, enc, delim


def read_csv_path(path, max_rows: int | None = None):
    with open(path, "rb") as fh:
        return read_csv_bytes(fh.read(), max_rows=max_rows)
