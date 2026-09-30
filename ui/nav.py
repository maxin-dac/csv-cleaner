from __future__ import annotations
import streamlit as st
from ui.i18n import t
from ui.theme import read_layout


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


def render_nav() -> str:
    lang = st.session_state.lang
    keys = [k for k, _ in PAGES]
    label = {k: ik for k, ik in PAGES}
    with st.container(key="dds-top-nav"):
        if hasattr(st, "segmented_control"):
            return st.segmented_control(
                "views",
                options=keys,
                format_func=lambda k: t(label[k], lang),
                key="nav_view",
                label_visibility="collapsed",
                width="stretch",
                required=True,
            )
        view = st.session_state.get("nav_view", "home")
        cols = st.columns(len(keys))
        for i, k in enumerate(keys):
            with cols[i]:
                if st.button(t(label[k], lang), key=f"nav_{k}", type=("primary" if k == view else "secondary")):
                    st.session_state.nav_view = k
                    st.rerun()
        return st.session_state.get("nav_view", "home")


def render_sidebar(version: str) -> None:
    lang = st.session_state.lang
    with st.sidebar:
        html = read_layout().format(
            app_name=t("app_name", lang),
            subtitle=t("app_subtitle", lang),
            version=f"{t('version_label', lang)} {version}",
            language_label=t("language_label", lang),
        )
        st.markdown(html, unsafe_allow_html=True)
        with st.container(key="dds-lang"):
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if st.button("FR", key="lang_fr", type=("primary" if lang == "fr" else "secondary"), use_container_width=True):
                    st.session_state.lang = "fr"
                    st.rerun()
            with c2:
                if st.button("EN", key="lang_en", type=("primary" if lang == "en" else "secondary"), use_container_width=True):
                    st.session_state.lang = "en"
                    st.rerun()
