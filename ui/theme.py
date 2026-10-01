from __future__ import annotations
import pathlib
import streamlit as st


ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def read_css() -> str:
    return (ASSETS / "styles.css").read_text(encoding="utf-8")


def read_svg() -> str:
    svg_path = ASSETS / "icons.svg"
    if svg_path.exists():
        return svg_path.read_text(encoding="utf-8")
    return ""


def load_css() -> None:
    st.markdown("<style>" + read_css() + "</style>" + read_svg(), unsafe_allow_html=True)
