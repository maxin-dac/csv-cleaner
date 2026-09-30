from __future__ import annotations
import re
import html
import streamlit as st
from ui.i18n import t


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _e(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def esc(value) -> str:
    return _e(value)


def md_bold_to_html(value) -> str:
    return _BOLD_RE.sub(r"<b>\1</b>", _e(value))


def page_header(title: str, sub: str) -> None:
    st.markdown(
        f'<div class="pg-h"><h1>{_e(title)}</h1><p>{_e(sub)}</p></div>',
        unsafe_allow_html=True,
    )


def section(title: str) -> None:
    st.markdown(f'<div class="sec-h">{_e(title)}</div>', unsafe_allow_html=True)


def card(inner_html: str) -> None:
    st.markdown(f'<div class="card">{inner_html}</div>', unsafe_allow_html=True)


def kv_grid(pairs) -> None:
    cells = "".join(f'<div class="kvcell"><div class="k">{_e(k)}</div><div class="v">{_e(v)}</div></div>' for k, v in pairs)
    st.markdown(f'<div class="kvgrid">{cells}</div>', unsafe_allow_html=True)


def warn_box(text: str) -> None:
    st.markdown(
        f'<div class="warnbox"><svg viewBox="0 0 24 24"><use href="#warning"></use></svg><span>{_e(text)}</span></div>',
        unsafe_allow_html=True,
    )


def ok_box(text: str) -> None:
    st.markdown(
        f'<div class="okbox"><svg viewBox="0 0 24 24"><use href="#check"></use></svg><span>{_e(text)}</span></div>',
        unsafe_allow_html=True,
    )


def conf_badge_html(v: float) -> str:
    pct = int(round(float(v) * 100))
    cls = "b-high" if pct >= 90 else ("b-mid" if pct >= 60 else "b-low")
    return f'<span class="badge {cls}">{pct}%</span>'


def status_badge_html(s: str) -> str:
    return f'<span class="badge s-{_e(s)}">{_e(s)}</span>'


def set_status(cid: str, status: str) -> None:
    ch = st.session_state.change_index.get(cid)
    if ch is not None:
        ch.status = status


def change_row(ch, lang: str) -> None:
    b = _e("" if ch.before is None else str(ch.before))
    a = _e("-" if ch.after is None else str(ch.after))
    col = _e("-" if ch.column is None else str(ch.column))
    row = "-" if ch.row_index is None else ch.row_index
    line = (
        f'<div class="chg">'
        f'<span class="ck">{_e(ch.kind)}</span>'
        f'<span class="ccol">{col}#{row}</span>'
        f'<span class="cdiff"><code>{b}</code><span class="arr">&rarr;</span><code>{a}</code></span>'
        f'<span class="crule">{_e(ch.rule)}</span>'
        f'{conf_badge_html(ch.confidence)}{status_badge_html(ch.status)}'
        f'</div>'
    )
    left, right = st.columns([5, 1])
    with left:
        st.markdown(line, unsafe_allow_html=True)
    with right:
        st.button(t("btn_accept", lang), key=f"acc_{ch.id}", on_click=set_status, args=(ch.id, "accepted"))
        st.button(t("btn_reject", lang), key=f"rej_{ch.id}", on_click=set_status, args=(ch.id, "rejected"))


def render_changes(changes, lang: str, cap: int = 200) -> None:
    if not changes:
        return
    shown = changes[:cap]
    for ch in shown:
        change_row(ch, lang)
    if len(changes) > cap:
        st.markdown(f'<div class="note">{cap} {t("more_note", lang)} · {len(changes) - cap} {t("and_more", lang)}</div>', unsafe_allow_html=True)
