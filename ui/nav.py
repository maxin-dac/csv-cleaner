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


def render_topbar(version: str) -> str:
    lang = st.session_state.get("lang", "en")
    keys = [key for key, _ in PAGES]
    labels = {key: label for key, label in PAGES}
    current = st.session_state.get("nav_view", "home")
    if current not in keys:
        current = keys[0]
    with st.container(key="suite-topbar"):
        nav_col, language_col, brand_col = st.columns([6.7, 1.1, 2.2])
        with nav_col:
            view = st.segmented_control(
                "views",
                options=keys,
                default=current,
                format_func=lambda key: t(labels[key], lang),
                key="suite-nav",
                required=True,
                label_visibility="collapsed",
                width="stretch",
            )
        with language_col:
            choice = st.segmented_control(
                t("language_label", lang),
                ["FR", "EN"],
                default="FR" if lang == "fr" else "EN",
                key="dds_lang_radio",
                required=True,
                label_visibility="collapsed",
            )
        with brand_col:
            version_text = version if version.startswith("v") else f"v{version}"
            st.markdown(
                f'<div class="suite-product"><span class="suite-product-logo">{_LOGO_SVG}</span>'
                f'<span class="suite-product-copy"><strong>{_e(t("app_name", lang))}</strong>'
                f'<small>{_e(version_text)}</small></span></div>',
                unsafe_allow_html=True,
            )
    new_lang = "fr" if choice == "FR" else "en"
    if new_lang != lang:
        st.session_state.lang = new_lang
        st.rerun()
    st.session_state.nav_view = view
    return view
