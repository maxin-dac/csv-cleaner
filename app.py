from __future__ import annotations
import pathlib
from urllib.parse import quote
import pandas as pd
import streamlit as st
from ui.theme import load_css
from ui.nav import render_nav, render_sidebar
from ui.i18n import t
from ui.components import page_header, section, card, kv_grid, warn_box, ok_box, render_changes, md_bold_to_html, esc
from core.models import Change, new_change_id
from core.io import read_csv_bytes, read_csv_path
from core.proposals import aggregate
from core.duplicates import find_duplicates
from core.apply import apply_changes
from report.builder import build_report
from report.exporters import export_report


def _read_version() -> str:
    root = pathlib.Path(__file__).resolve().parent
    vf = root / "VERSION"
    try:
        return "v" + vf.read_text(encoding="utf-8").strip()
    except OSError:
        return "v0.1.0"


VERSION = _read_version()
ROOT = pathlib.Path(__file__).resolve().parent
CASTABLE = {"int64", "float64", "bool", "category"}
DTYPES = ["string", "int64", "float64", "bool", "category", "datetime"]
CASES = ["keep", "lower", "upper", "title"]
MAX_ROWS = 200000
CAP = 200
SAMPLES = [("messy", "samp_messy"), ("dates", "samp_dates"), ("dupes", "samp_dupes")]
_FAV_BODY = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect width='24' height='24' rx='6' fill='#4f46e5'/><g fill='none' stroke='#ffffff' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'><path d='M14 6l4 4-7 7-4-4z'/><path d='M7 13l-1.5 5.5L11 17'/></g></svg>"
FAVICON = "data:image/svg+xml," + quote(_FAV_BODY, safe="")


def init_state() -> None:
    s = st.session_state
    s.setdefault("lang", "en")
    s.setdefault("nav_view", "home")
    s.setdefault("df", None)
    s.setdefault("filename", None)
    s.setdefault("profiles", None)
    s.setdefault("changes", None)
    s.setdefault("change_index", {})
    s.setdefault("warnings", [])
    s.setdefault("blocked", False)
    s.setdefault("analyzed", False)


def clean_prefixes(*prefixes) -> None:
    s = st.session_state
    for k in list(s.keys()):
        if any(str(k).startswith(p) for p in prefixes):
            del s[k]


def load_df(df, name, truncated, enc, delim) -> None:
    s = st.session_state
    s.df = df
    s.filename = name
    s.profiles = None
    s.changes = None
    s.change_index = {}
    s.warnings = []
    s.blocked = False
    s.analyzed = False
    clean_prefixes("ovr_", "acc_", "rej_", "opt_dupkeys")
    s["_trunc_note"] = f"truncated to {MAX_ROWS} rows" if truncated else None
    s["_meta"] = {"enc": enc, "delim": delim}


def run_analysis() -> None:
    s = st.session_state
    df = s.df
    if df is None:
        return
    profiles, dr = aggregate(
        df,
        threshold=s.get("opt_thr", 0.95),
        case=s.get("opt_case", "keep"),
        cat_threshold=int(s.get("opt_catthr", 90)),
        unify_nulls=bool(s.get("opt_unify", True)),
        dup_keys=(s.get("opt_dupkeys", []) or None),
        dup_threshold=int(s.get("opt_dupthr", 85)),
    )
    s.profiles = profiles
    s.changes = dr.changes
    s.change_index = {c.id: c for c in dr.changes}
    s.warnings = dr.warnings
    s.blocked = dr.blocked_export
    s.analyzed = True


def apply_override(col: str) -> None:
    s = st.session_state
    new = s.get(f"ovr_{col}")
    profiles = s.profiles
    if profiles is None or new is None or new == profiles[col].dtype_inferred:
        return
    profiles[col].dtype_inferred = new
    keep = [c for c in s.changes if not (c.kind == "type_cast" and c.column == col)]
    for c in s.changes:
        if c.kind == "type_cast" and c.column == col:
            s.change_index.pop(c.id, None)
    if new in CASTABLE:
        nc = Change(new_change_id(), "type_cast", col, None, "string", new, f"cast:{new}", 1.0)
        keep.append(nc)
        s.change_index[nc.id] = nc
    s.changes = keep


def redetect_dupes() -> None:
    s = st.session_state
    df = s.df
    keys = s.get("opt_dupkeys", []) or []
    if df is None or not keys:
        return
    ndr = find_duplicates(df, keys, threshold=int(s.get("opt_dupthr", 85)))
    keep = [c for c in s.changes if c.kind != "dedup"]
    for c in s.changes:
        if c.kind == "dedup":
            s.change_index.pop(c.id, None)
    keep.extend(ndr.changes)
    for c in ndr.changes:
        s.change_index[c.id] = c
    s.changes = keep
    s.warnings = [w for w in s.warnings if "duplicate groups" not in w and "truncated" not in w] + ndr.warnings


def counts(changes) -> dict:
    out = {"accepted": 0, "pending": 0, "rejected": 0}
    if changes:
        for c in changes:
            out[c.status] = out.get(c.status, 0) + 1
    return out


def by_kind(changes, kinds) -> list:
    if not changes:
        return []
    return [c for c in changes if c.kind in kinds]


def warn_list_html(warnings) -> str:
    return "<ul>" + "".join(f"<li>{esc(w)}</li>" for w in warnings) + "</ul>"


def profiles_df(profiles) -> pd.DataFrame:
    rows = []
    for name in sorted(profiles.keys()):
        p = profiles[name]
        rows.append({
            "column": name,
            "dtype": p.dtype_inferred,
            "confidence": round(p.confidence, 3),
            "missing": round(p.null_like_rate, 3),
            "distinct": p.distinct,
            "flags": ", ".join(p.flags) if p.flags else "-",
        })
    return pd.DataFrame(rows)


def page_home() -> None:
    lang = st.session_state.lang
    page_header(t("home_title", lang), t("home_sub", lang))
    section(t("home_how", lang))
    steps = "".join(f"<li>{md_bold_to_html(t(k, lang))}</li>" for k in ("home_s1", "home_s2", "home_s3"))
    card(f"<ol>{steps}</ol>")
    section(t("home_status", lang))
    s = st.session_state
    df = s.df
    cc = counts(s.changes)
    kv_grid([
        (t("st_rows", lang), (len(df) if df is not None else "-")),
        (t("st_cols", lang), (len(df.columns) if df is not None else "-")),
        (t("st_pending", lang), cc["pending"]),
        (t("st_accepted", lang), cc["accepted"]),
        (t("st_rejected", lang), cc["rejected"]),
    ])
    if df is None:
        st.markdown(f'<div class="note">{t("st_notloaded", lang)}</div>', unsafe_allow_html=True)
    elif s.blocked:
        warn_box(t("st_blocked_yes", lang))
    else:
        ok_box(t("st_blocked_no", lang))


def page_import() -> None:
    lang = st.session_state.lang
    s = st.session_state
    page_header(t("imp_title", lang), t("imp_sub", lang))
    up = st.file_uploader(t("imp_upload", lang), type=["csv"], key="uploader")
    if up is not None:
        df, trunc, enc, delim = read_csv_bytes(up.getvalue(), max_rows=MAX_ROWS)
        load_df(df, up.name, trunc, enc, delim)
    csm = st.columns(3)
    for i, (slug, ik) in enumerate(SAMPLES):
        with csm[i]:
            if st.button(t(ik, lang), key=f"samp_{slug}", use_container_width=True):
                path = ROOT / "data" / f"sample_{slug}.csv"
                df, trunc, enc, delim = read_csv_path(path, max_rows=MAX_ROWS)
                load_df(df, path.name, trunc, enc, delim)
    if s.df is not None:
        meta = s.get("_meta", {})
        section(t("imp_file", lang))
        kv_grid([
            (t("imp_file", lang), s.filename),
            (t("imp_shape", lang), f"{len(s.df)} x {len(s.df.columns)}"),
            ("encoding", meta.get("enc", "-")),
            ("delimiter", repr(meta.get("delim", ","))),
        ])
        if s.get("_trunc_note"):
            warn_box(s["_trunc_note"])
        section(t("imp_opts", lang))
        cols = st.columns(2)
        with cols[0]:
            st.slider(t("imp_thresh", lang), 0.5, 1.0, 0.95, 0.01, key="opt_thr")
            st.selectbox(t("imp_case", lang), CASES, index=0, key="opt_case", format_func=lambda x: t(f"case_{x}", lang))
            st.slider(t("imp_catthr", lang), 60, 100, 90, 1, key="opt_catthr")
            st.checkbox(t("imp_unify", lang), value=True, key="opt_unify")
        with cols[1]:
            st.multiselect(t("imp_dupkeys", lang), list(s.df.columns), default=[], key="opt_dupkeys")
            st.slider(t("imp_dupthr", lang), 50, 100, 85, 1, key="opt_dupthr")
        bcols = st.columns(2)
        with bcols[0]:
            if st.button(t("imp_run", lang), key="run", type="primary", use_container_width=True):
                run_analysis()
                st.rerun()
        with bcols[1]:
            if st.button(t("imp_reset", lang), key="reset", use_container_width=True):
                s.df = None
                s.filename = None
                s.profiles = None
                s.changes = None
                s.change_index = {}
                s.warnings = []
                s.blocked = False
                s.analyzed = False
                clean_prefixes("ovr_", "acc_", "rej_", "opt_dupkeys")
                st.rerun()
        if s.analyzed:
            ok_box(t("imp_analyzed", lang))
        else:
            st.markdown(f'<div class="note">{t("imp_notyet", lang)}</div>', unsafe_allow_html=True)


def require_df() -> bool:
    if st.session_state.df is None:
        warn_box(t("err_nofile", st.session_state.lang))
        return False
    return True


def require_analysis() -> bool:
    if not st.session_state.analyzed:
        warn_box(t("err_noanalysis", st.session_state.lang))
        return False
    return True


def page_overview() -> None:
    lang = st.session_state.lang
    s = st.session_state
    page_header(t("ov_title", lang), t("ov_sub", lang))
    if not require_df():
        return
    kv_grid([
        (t("st_rows", lang), len(s.df)),
        (t("st_cols", lang), len(s.df.columns)),
    ])
    if not s.analyzed:
        st.markdown(f'<div class="note">{t("imp_notyet", lang)}</div>', unsafe_allow_html=True)
        return
    section(t("ov_dtypes", lang))
    st.dataframe(profiles_df(s.profiles), use_container_width=True, hide_index=True)
    section(t("ov_warnings", lang))
    if s.warnings:
        card(warn_list_html(s.warnings))
    else:
        ok_box(t("ov_nowarn", lang))


def page_schema() -> None:
    lang = st.session_state.lang
    s = st.session_state
    page_header(t("sch_title", lang), t("sch_sub", lang))
    if not (require_df() and require_analysis()):
        return
    st.dataframe(profiles_df(s.profiles), use_container_width=True, hide_index=True)
    section(t("sch_override", lang))
    for col in list(s.profiles.keys())[:60]:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f'<div class="ccol" style="padding-top:6px">{esc(col)}</div>', unsafe_allow_html=True)
        with c2:
            cur = s.profiles[col].dtype_inferred
            idx = DTYPES.index(cur) if cur in DTYPES else 0
            st.selectbox(t("sch_dtype", lang), DTYPES, index=idx, key=f"ovr_{col}", label_visibility="collapsed", on_change=apply_override, args=(col,))


def page_quality() -> None:
    lang = st.session_state.lang
    s = st.session_state
    page_header(t("q_title", lang), t("q_sub", lang))
    if not (require_df() and require_analysis()):
        return
    items = by_kind(s.changes, {"text_norm", "cat_merge", "coherence_fix"})
    if not items:
        ok_box(t("q_none", lang))
        return
    render_changes(items, lang, cap=CAP)


def page_dates() -> None:
    lang = st.session_state.lang
    s = st.session_state
    page_header(t("dt_title", lang), t("dt_sub", lang))
    if not (require_df() and require_analysis()):
        return
    if s.blocked:
        warn_box(t("dt_blocked", lang))
    items = by_kind(s.changes, {"date_norm"})
    if not items:
        ok_box(t("dt_none", lang))
        return
    render_changes(items, lang, cap=CAP)


def page_dupes() -> None:
    lang = st.session_state.lang
    s = st.session_state
    page_header(t("dp_title", lang), t("dp_sub", lang))
    if not (require_df() and require_analysis()):
        return
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.multiselect(t("dp_keys", lang), list(s.df.columns), default=s.get("opt_dupkeys", []), key="opt_dupkeys")
    with c2:
        st.slider(t("dp_thr", lang), 50, 100, int(s.get("opt_dupthr", 85)), 1, key="opt_dupthr")
    with c3:
        st.write("")
        if st.button(t("dp_redetect", lang), key="redup", use_container_width=True):
            redetect_dupes()
            st.rerun()
    items = by_kind(s.changes, {"dedup"})
    if not items:
        ok_box(t("dp_none", lang))
        return
    render_changes(items, lang, cap=CAP)


def page_report() -> None:
    lang = st.session_state.lang
    s = st.session_state
    page_header(t("rp_title", lang), t("rp_sub", lang))
    if not (require_df() and require_analysis()):
        return
    clean, summ = apply_changes(s.df, s.changes, s.profiles)
    report = build_report(s.profiles, s.changes, s.warnings, s.blocked, summ)
    cc = counts(s.changes)
    kv_grid([
        (t("st_rows", lang), f"{summ['rows_before']} -> {summ['rows_after']}"),
        (t("st_accepted", lang), cc["accepted"]),
        (t("st_pending", lang), cc["pending"]),
        (t("st_rejected", lang), cc["rejected"]),
    ])
    if s.blocked:
        warn_box(t("rp_blocked", lang))
    section(t("rp_preview", lang))
    st.dataframe(clean.head(50), use_container_width=True, hide_index=True)
    section(t("ov_warnings", lang))
    if s.warnings:
        card(warn_list_html(s.warnings))
    else:
        ok_box(t("ov_nowarn", lang))
    dcols = st.columns(4)
    csv_bytes = clean.to_csv(index=False).encode("utf-8")
    with dcols[0]:
        st.download_button(t("rp_dl_csv", lang), data=csv_bytes, file_name="clean.csv", mime="text/csv", use_container_width=True, disabled=bool(s.blocked))
    with dcols[1]:
        st.download_button(t("rp_dl_md", lang), data=export_report(report, "markdown").encode("utf-8"), file_name="report.md", mime="text/markdown", use_container_width=True)
    with dcols[2]:
        st.download_button(t("rp_dl_json", lang), data=export_report(report, "json").encode("utf-8"), file_name="report.json", mime="application/json", use_container_width=True)
    with dcols[3]:
        st.download_button(t("rp_dl_html", lang), data=export_report(report, "html").encode("utf-8"), file_name="report.html", mime="text/html", use_container_width=True)


ROUTES = {
    "home": page_home,
    "import": page_import,
    "overview": page_overview,
    "schema": page_schema,
    "quality": page_quality,
    "dates": page_dates,
    "dupes": page_dupes,
    "report": page_report,
}


def main() -> None:
    init_state()
    st.set_page_config(page_title=t("app_name", st.session_state.lang), page_icon=FAVICON, layout="wide", initial_sidebar_state="expanded")
    load_css()
    render_sidebar(VERSION)
    view = render_nav()
    ROUTES[view]()


main()
