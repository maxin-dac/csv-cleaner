from __future__ import annotations
import json
import pathlib
import pandas as pd
from core.models import Change, ColumnProfile, WarningMessage


SESSION_FILE = pathlib.Path(".streamlit/session_state.json")


def _serialize_profile(p: ColumnProfile) -> dict:
    return {
        "name": p.name,
        "dtype_inferred": p.dtype_inferred,
        "confidence": p.confidence,
        "null_like_rate": p.null_like_rate,
        "distinct": p.distinct,
        "samples": p.samples,
        "flags": p.flags,
        "numeric_thousands": p.numeric_thousands,
        "numeric_decimal": p.numeric_decimal,
    }


def _deserialize_profile(d: dict) -> ColumnProfile:
    return ColumnProfile(**d)


def _serialize_change(c: Change) -> dict:
    return {
        "id": c.id,
        "kind": c.kind,
        "column": c.column,
        "row_index": c.row_index,
        "before": c.before,
        "after": c.after,
        "rule": c.rule,
        "confidence": c.confidence,
        "status": c.status,
    }


def _deserialize_change(d: dict) -> Change:
    return Change(**d)


def _serialize_warning(w) -> dict:
    if isinstance(w, str):
        return {"type": "str", "value": w}
    return {"type": "WarningMessage", "key": w.key, "params": w.params}


def _deserialize_warning(d: dict):
    if d["type"] == "str":
        return d["value"]
    return WarningMessage(key=d["key"], params=d["params"])


def save_session(state: dict) -> None:
    try:
        data = {
            "lang": state.get("lang"),
            "page": state.get("page"),
            "filename": state.get("filename"),
            "analyzed": state.get("analyzed"),
            "blocked": state.get("blocked"),
            "df": state["df"].to_dict(orient="records") if state.get("df") is not None else None,
            "profiles": {k: _serialize_profile(v) for k, v in state.get("profiles", {}).items()} if state.get("profiles") else None,
            "changes": [_serialize_change(c) for c in state.get("changes", [])],
            "warnings": [_serialize_warning(w) for w in state.get("warnings", [])],
        }
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def load_session() -> dict | None:
    try:
        if not SESSION_FILE.exists():
            return None
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        state = {
            "lang": data.get("lang"),
            "page": data.get("page"),
            "filename": data.get("filename"),
            "analyzed": data.get("analyzed"),
            "blocked": data.get("blocked"),
            "df": pd.DataFrame(data["df"]) if data.get("df") else None,
            "profiles": {k: _deserialize_profile(v) for k, v in data["profiles"].items()} if data.get("profiles") else None,
            "changes": [_deserialize_change(c) for c in data.get("changes", [])],
            "warnings": [_deserialize_warning(w) for w in data.get("warnings", [])],
            "change_index": {c.id: c for c in [_deserialize_change(c) for c in data.get("changes", [])]},
        }
        return state
    except Exception:
        return None


def clear_session() -> None:
    try:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
    except Exception:
        pass
