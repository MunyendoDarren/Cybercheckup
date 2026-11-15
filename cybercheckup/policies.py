"""Fill the policy templates with the business's details."""
from __future__ import annotations

import html
import re
from datetime import date, timedelta

import markdown

from .model import DATA, Assessment

TITLES = {
    "password": "Passwords and account access policy",
    "acceptable-use": "Staff acceptable use and security rules",
    "data-protection": "Customer and personal data policy",
    "backup": "Backup and recovery policy",
    "payments": "Payment verification policy",
    "devices": "Devices, Wi-Fi and mobile phone policy",
    "incident-response": "If something goes wrong: incident response plan",
}


def context(a: Assessment) -> dict[str, str]:
    on = date.fromisoformat(a.on)
    return {
        "business_name": a.business.name,
        "owner": a.business.owner,
        "date": a.on,
        "review_date": (on + timedelta(days=365)).isoformat(),
        "staff_count": str(a.business.staff),
    }


def _fill(text: str, ctx: dict[str, str]) -> str:
    return re.sub(r"\{\{(\w+)\}\}", lambda m: ctx.get(m.group(1), m.group(0)), text)


def render_markdown(policy_id: str, a: Assessment) -> str:
    template = (DATA / "policies" / f"{policy_id}.md").read_text(encoding="utf-8")
    return _fill(template, context(a))


def render_body_html(policy_id: str, a: Assessment) -> str:
    """HTML body. Business details are escaped so a name cannot inject markup."""
    template = (DATA / "policies" / f"{policy_id}.md").read_text(encoding="utf-8")
    safe = {k: html.escape(v) for k, v in context(a).items()}
    return markdown.markdown(_fill(template, safe), extensions=["tables"])
