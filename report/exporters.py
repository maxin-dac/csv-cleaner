from __future__ import annotations
import json
import html


def _txt(value):
    return "" if value is None else str(value)


def _md(value):
    return _txt(value).replace("|", "\\|")


def export_json(report):
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True)


def export_markdown(report):
    lines = []
    lines.append("# Data Cleaning Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- rows before: {report['apply_summary']['rows_before']}")
    lines.append(f"- rows after: {report['apply_summary']['rows_after']}")
    lines.append(f"- blocked export: {'yes' if report['blocked_export'] else 'no'}")
    lines.append(f"- total changes: {sum(report['counts_by_kind'].values())}")
    lines.append("")
    lines.append("### Counts by kind")
    lines.append("")
    for kind in sorted(report["counts_by_kind"]):
        lines.append(f"- {kind}: {report['counts_by_kind'][kind]}")
    lines.append("")
    lines.append("### Counts by status")
    lines.append("")
    for st in ("accepted", "pending", "rejected"):
        lines.append(f"- {st}: {report['counts_by_status'].get(st, 0)}")
    lines.append("")
    lines.append("## Warnings")
    lines.append("")
    if report["warnings"]:
        for w in report["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Columns")
    lines.append("")
    lines.append("| column | dtype | confidence | null rate | distinct | flags | changes accepted |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for c in report["columns"]:
        flags = ", ".join(c["flags"]) if c["flags"] else "-"
        lines.append(
            f"| {_md(c['name'])} | {_md(c['dtype'])} | {c['confidence']} | {c['null_like_rate']} "
            f"| {c['distinct']} | {_md(flags)} | {c['changes_accepted']} |"
        )
    lines.append("")
    lines.append("## Changes")
    lines.append("")
    lines.append("| status | kind | column | row | before | after | rule | confidence |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for ch in report["changes"]:
        row = "-" if ch["row_index"] is None else ch["row_index"]
        col = "-" if ch["column"] is None else _md(ch["column"])
        lines.append(
            f"| {_md(ch['status'])} | {_md(ch['kind'])} | {col} | {row} "
            f"| {_md(ch['before'])} | {_md(ch['after'])} | {_md(ch['rule'])} | {ch['confidence']} |"
        )
    lines.append("")
    lines.append("## Rules triggered")
    lines.append("")
    for r in report["rules_triggered"]:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("## Apply summary")
    lines.append("")
    lines.append("applied by kind:")
    for k in sorted(report["apply_summary"]["applied_by_kind"]):
        lines.append(f"- {k}: {report['apply_summary']['applied_by_kind'][k]}")
    lines.append("")
    lines.append("casts:")
    if report["apply_summary"]["casts"]:
        for x in report["apply_summary"]["casts"]:
            lines.append(f"- {x}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("mismatches:")
    if report["apply_summary"]["mismatches"]:
        for m in report["apply_summary"]["mismatches"]:
            lines.append(f"- {m}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


_CSS = (
    "*{box-sizing:border-box;margin:0;padding:0;transition:none!important;animation:none!important}"
    "body{font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
    "background:#f5f7fb;color:#1f2937;line-height:1.5}"
    "header{background:#2f6bed;color:#fff;padding:18px 28px}"
    "header h1{font-size:20px;font-weight:700}"
    "main{max-width:1100px;margin:0 auto;padding:24px 28px}"
    "section{background:#fff;border:1px solid #e5e7eb;border-radius:10px;"
    "padding:18px 20px;margin-bottom:18px}"
    "h2{font-size:15px;font-weight:700;margin-bottom:12px;color:#111827}"
    "table{width:100%;border-collapse:collapse;font-size:13px}"
    "th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #eef0f4;vertical-align:top}"
    "th{color:#6b7280;font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:.04em}"
    "code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;"
    "background:#f3f4f6;padding:1px 5px;border-radius:4px}"
    "ul{margin-left:18px;font-size:13px}"
    ".badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:600}"
    ".accepted{background:#dcfce7;color:#166534}"
    ".pending{background:#fef3c7;color:#92400e}"
    ".rejected{background:#fee2e2;color:#991b1b}"
    ".kv{font-size:13px}.kv b{display:inline-block;min-width:140px;color:#6b7280;font-weight:600}"
    ".empty{color:#9ca3af;font-size:13px}"
)


def _esc(value):
    return html.escape(_txt(value))


def export_html(report):
    p = []
    p.append("<!DOCTYPE html>")
    p.append("<html lang=\"en\"><head><meta charset=\"utf-8\">")
    p.append("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">")
    p.append("<title>Data Cleaning Report</title>")
    p.append(f"<style>{_CSS}</style></head><body>")
    p.append("<header><h1>Data Cleaning Report</h1></header><main>")

    p.append("<section><h2>Summary</h2>")
    p.append(f"<p class=\"kv\"><b>rows before</b>{report['apply_summary']['rows_before']}</p>")
    p.append(f"<p class=\"kv\"><b>rows after</b>{report['apply_summary']['rows_after']}</p>")
    p.append(f"<p class=\"kv\"><b>blocked export</b>{'yes' if report['blocked_export'] else 'no'}</p>")
    p.append(f"<p class=\"kv\"><b>total changes</b>{sum(report['counts_by_kind'].values())}</p>")
    p.append("</section>")

    p.append("<section><h2>Counts</h2>")
    p.append("<p class=\"kv\"><b>by kind</b>")
    if report["counts_by_kind"]:
        p.append(", ".join(f"{_esc(k)}: {v}" for k, v in sorted(report["counts_by_kind"].items())))
    else:
        p.append("<span class=\"empty\">none</span>")
    p.append("</p>")
    p.append("<p class=\"kv\"><b>by status</b>")
    p.append(", ".join(f"{st}: {report['counts_by_status'].get(st, 0)}" for st in ("accepted", "pending", "rejected")))
    p.append("</p></section>")

    p.append("<section><h2>Warnings</h2>")
    if report["warnings"]:
        p.append("<ul>")
        for w in report["warnings"]:
            p.append(f"<li>{_esc(w)}</li>")
        p.append("</ul>")
    else:
        p.append("<p class=\"empty\">none</p>")
    p.append("</section>")

    p.append("<section><h2>Columns</h2><table><thead><tr>"
             "<th>column</th><th>dtype</th><th>confidence</th><th>null rate</th>"
             "<th>distinct</th><th>flags</th><th>changes accepted</th></tr></thead><tbody>")
    for c in report["columns"]:
        flags = ", ".join(c["flags"]) if c["flags"] else "-"
        p.append(
            f"<tr><td><code>{_esc(c['name'])}</code></td><td>{_esc(c['dtype'])}</td>"
            f"<td>{c['confidence']}</td><td>{c['null_like_rate']}</td><td>{c['distinct']}</td>"
            f"<td>{_esc(flags)}</td><td>{c['changes_accepted']}</td></tr>"
        )
    p.append("</tbody></table></section>")

    p.append("<section><h2>Changes</h2><table><thead><tr>"
             "<th>status</th><th>kind</th><th>column</th><th>row</th>"
             "<th>before</th><th>after</th><th>rule</th><th>confidence</th></tr></thead><tbody>")
    for ch in report["changes"]:
        row = "-" if ch["row_index"] is None else ch["row_index"]
        col = "-" if ch["column"] is None else f"<code>{_esc(ch['column'])}</code>"
        st = ch["status"]
        p.append(
            f"<tr><td><span class=\"badge { _esc(st) }\">{_esc(st)}</span></td>"
            f"<td>{_esc(ch['kind'])}</td><td>{col}</td><td>{row}</td>"
            f"<td><code>{_esc(ch['before'])}</code></td><td><code>{_esc(ch['after'])}</code></td>"
            f"<td>{_esc(ch['rule'])}</td><td>{ch['confidence']}</td></tr>"
        )
    p.append("</tbody></table></section>")

    p.append("<section><h2>Rules triggered</h2>")
    if report["rules_triggered"]:
        p.append("<ul>")
        for r in report["rules_triggered"]:
            p.append(f"<li><code>{_esc(r)}</code></li>")
        p.append("</ul>")
    else:
        p.append("<p class=\"empty\">none</p>")
    p.append("</section>")

    p.append("<section><h2>Apply summary</h2>")
    p.append("<p class=\"kv\"><b>applied by kind</b>")
    if report["apply_summary"]["applied_by_kind"]:
        p.append(", ".join(f"{_esc(k)}: {v}" for k, v in sorted(report["apply_summary"]["applied_by_kind"].items())))
    else:
        p.append("<span class=\"empty\">none</span>")
    p.append("</p>")
    p.append("<p class=\"kv\"><b>casts</b>")
    if report["apply_summary"]["casts"]:
        p.append(", ".join(f"<code>{_esc(x)}</code>" for x in report["apply_summary"]["casts"]))
    else:
        p.append("<span class=\"empty\">none</span>")
    p.append("</p>")
    p.append("<p class=\"kv\"><b>mismatches</b>")
    if report["apply_summary"]["mismatches"]:
        p.append(", ".join(f"<code>{_esc(m)}</code>" for m in report["apply_summary"]["mismatches"]))
    else:
        p.append("<span class=\"empty\">none</span>")
    p.append("</p></section>")

    p.append("</main></body></html>")
    return "".join(p)


def export_report(report, fmt):
    f = _txt(fmt).lower()
    if f == "json":
        return export_json(report)
    if f in ("md", "markdown"):
        return export_markdown(report)
    if f == "html":
        return export_html(report)
    raise ValueError(f"unknown export format: {fmt}")