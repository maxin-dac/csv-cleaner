import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import ui.i18n as i18n
import ui.theme as theme
import ui.nav as nav
import ui.components as comp
import core.io as io
import report.builder as builder
import report.exporters as exporters


CRITICAL = [
    "app_name", "app_subtitle", "language_label", "home_title", "home_sub", "home_how",
    "home_s1", "home_s2", "home_s3", "home_status", "imp_title", "imp_run", "imp_opts",
    "ov_title", "sch_title", "q_title", "dt_title", "dp_title", "rp_title", "rp_dl_csv",
    "btn_accept", "btn_reject", "err_nofile", "err_noanalysis", "samp_messy", "samp_dates", "samp_dupes",
]


def test_i18n_nav_keys_present_both_langs():
    for _key, ik in nav.PAGES:
        for lang in ("fr", "en"):
            assert i18n.t(ik, lang) != ik


def test_i18n_critical_keys_present_both_langs():
    for k in CRITICAL:
        for lang in ("fr", "en"):
            assert i18n.t(k, lang) != k


def test_i18n_unknown_key_returns_key():
    assert i18n.t("does_not_exist_zz", "en") == "does_not_exist_zz"


def test_io_detect_and_sniff():
    assert io.detect_encoding("café".encode("utf-8")) == "utf-8"
    assert io.detect_encoding(b"\xff\xfe\x00\x00abc") in io.ENCODINGS
    assert io.sniff_delimiter("a;b;c\n1;2;3") == ";"
    assert io.sniff_delimiter("no delimiter here") == ","


def test_components_escape_and_badges():
    assert comp._e('<a>&"') == "&lt;a&gt;&amp;&quot;"
    assert "b-high" in comp.conf_badge_html(0.97)
    assert "b-low" in comp.conf_badge_html(0.3)
    assert "s-accepted" in comp.status_badge_html("accepted")


def test_assets_readable():
    css = theme.read_css()
    assert "--primary:" in css
    assert ".st-key-dds-top-nav" in css
    assert "<symbol" in theme.read_svg()
    assert "{app_name}" in theme.read_layout()


def test_report_modules_importable():
    assert callable(builder.build_report)
    assert callable(exporters.export_report)
