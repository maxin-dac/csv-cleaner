from __future__ import annotations
import csv
import io
import pandas as pd


ENCODINGS = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
UTF8_BOM = b"\xef\xbb\xbf"

try:
    from charset_normalizer import from_bytes as _from_bytes
except ImportError:  # pragma: no cover
    _from_bytes = None


def detect_encoding(data: bytes, hint: str | None = None) -> str:
    if hint is not None and hint != "auto":
        return hint
    if data.startswith(UTF8_BOM):
        return "utf-8-sig"
    if _from_bytes is not None:
        try:
            best = _from_bytes(data[:1_000_000]).best()
            if best is not None and best.encoding:
                return str(best.encoding)
        except Exception:
            pass
    for enc in ENCODINGS:
        try:
            data.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def sniff_delimiter(sample: str, hint: str | None = None) -> str:
    if hint is not None and hint != "auto":
        return hint
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        counts = {
            ",": sample.count(","),
            ";": sample.count(";"),
            "\t": sample.count("\t"),
            "|": sample.count("|"),
        }
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","


def read_csv_bytes(
    data: bytes,
    max_rows: int | None = None,
    sep: str = "auto",
    encoding: str = "auto",
):
    enc = detect_encoding(data, hint=None if encoding == "auto" else encoding)
    text = data.decode(enc, errors="replace")
    delim = sniff_delimiter(text[:65536], hint=None if sep == "auto" else sep)
    df = pd.read_csv(io.StringIO(text), sep=delim, dtype=str, keep_default_na=False, engine="python")
    truncated = False
    if max_rows is not None and len(df) > max_rows:
        df = df.iloc[:max_rows].copy()
        truncated = True
    df.columns = [str(c) for c in df.columns]
    return df, truncated, enc, delim


def read_csv_path(
    path,
    max_rows: int | None = None,
    sep: str = "auto",
    encoding: str = "auto",
):
    with open(path, "rb") as fh:
        return read_csv_bytes(fh.read(), max_rows=max_rows, sep=sep, encoding=encoding)
