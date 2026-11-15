"""Write every deliverable for one assessment into a folder."""
from __future__ import annotations

import json
from pathlib import Path

import markdown

from . import briefing, policies
from .model import Assessment
from .report import build_csv, build_report, page


def write_all(a: Assessment, out: Path) -> dict[str, Path]:
    out = Path(out)
    (out / "policies").mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}

    def put(name: str, text: str) -> None:
        path = out / name
        path.write_text(text, encoding="utf-8", newline="\n")
        files[name] = path

    put("report.html", build_report(a))
    put("action-plan.csv", build_csv(a))
    put("assessment.json", json.dumps(a.to_dict(), indent=2))

    md = briefing.build_markdown(a)
    put("staff-briefing.md", md)
    main_md = md.split("## Print and pin")[0]
    html_body = markdown.markdown(_escape_name(main_md, a), extensions=["tables"]) + briefing.poster_html(a)
    put("staff-briefing.html", page(f"Staff briefing: {a.business.name}", html_body))

    for pid in a.policies_needed():
        put(f"policies/{pid}.md", policies.render_markdown(pid, a))
        body = policies.render_body_html(pid, a)
        put(f"policies/{pid}.html", page(policies.TITLES[pid], body))
    return files


def _escape_name(text: str, a: Assessment) -> str:
    """The briefing markdown embeds the business and owner names: escape them for HTML."""
    import html

    for raw in (a.business.name, a.business.owner):
        text = text.replace(raw, html.escape(raw))
    return text
