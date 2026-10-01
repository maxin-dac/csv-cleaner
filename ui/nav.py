from __future__ import annotations
import html
import streamlit as st
from ui.i18n import t


PAGES = [
    ("home", "nav_home"),
    ("import", "nav_import"),
    ("overview", "nav_overview"),
    ("schema", "nav_schema"),
    ("quality", "nav_quality"),
    ("dates", "nav_dates"),
    ("dupes", "nav_dupes"),
    ("report", "nav_report"),
]

_TAGLINE = {
    "en": "Smart CSV cleansing assistant",
    "fr": "Assistant intelligent de nettoyage CSV",
}

_LOGO_SVG = (
    '<svg class="logo-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M14 6l4 4-7 7-4-4z"/>'
    '<path d="M7 13l-1.5 5.5L11 17"/>'
    '</svg>'
)


def _e(value: str) -> str:
    return html.escape(str(value))


def render_sidebar(version: str) -> None:
    lang = st.session_state.get("lang", "en")

    st.sidebar.markdown(
        f'<div class="idcard"><div class="logo-wrap">{_LOGO_SVG}</div>'
        f'<div class="idmeta"><div class="idtitle">{_e(t("app_name", lang))}</div>'
        f'<div class="idsub">{_e(_TAGLINE.get(lang, _TAGLINE["en"]))}</div>'
        f'<div class="idver">version v{_e(version)}</div></div></div>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        f'<div class="lang-label">{_e(t("language_label", lang))}</div>',
        unsafe_allow_html=True,
    )

    choice = st.sidebar.radio(
        t("language_label", lang),
        ["FR", "EN"],
        index=0 if lang == "fr" else 1,
        horizontal=True,
        key="dds_lang_radio",
        label_visibility="collapsed",
    )
    new_lang = "fr" if choice == "FR" else "en"
    if new_lang != lang:
        st.session_state.lang = new_lang
        st.rerun()


def render_nav() -> str:
    lang = st.session_state.get("lang", "en")
    keys = [k for k, _ in PAGES]
    labels = {k: ik for k, ik in PAGES}
    with st.container(key="dds-top-nav"):
        if hasattr(st, "segmented_control"):
            return st.segmented_control(
                "views",
                options=keys,
                format_func=lambda k: t(labels[k], lang),
                key="nav_view",
                label_visibility="collapsed",
                width="stretch",
                required=True,
            )
        view = st.session_state.get("nav_view", "home")
        cols = st.columns(len(keys))
        for i, k in enumerate(keys):
            with cols[i]:
                if st.button(t(labels[k], lang), key=f"nav_{k}", type=("primary" if k == view else "secondary")):
                    st.session_state.nav_view = k
                    st.rerun()
        return st.session_state.get("nav_view", "home")
