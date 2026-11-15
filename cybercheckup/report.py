"""HTML report and CSV action plan. Output files make no network requests."""
from __future__ import annotations

import csv
import html
import io

from .model import ANSWER_LABEL, EFFORT_LABEL, PHASES, Assessment, Finding
from .policies import TITLES

esc = html.escape

CSS = """
:root{--ink:#12263a;--muted:#55677a;--paper:#f4f7f9;--panel:#fff;--line:#d3dde5;
--ok:#2f7d4f;--fair:#0f766e;--risk:#a85a00;--bad:#b42318;--bar:#e3eaef}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,"Segoe UI",Roboto,sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:30px;line-height:1.15;margin:0 0 6px;letter-spacing:-.015em}
h2{font-size:21px;margin:40px 0 6px;letter-spacing:-.01em}
h3{font-size:17px;margin:0}
p{margin:0 0 12px;max-width:68ch}
a{color:var(--fair)}
.sub{color:var(--muted)}
.summary{display:grid;grid-template-columns:200px 1fr;gap:28px;align-items:center;margin:24px 0 8px;
 padding:24px;background:var(--panel);border:1px solid var(--line);border-radius:12px}
.score{text-align:center}
.score b{display:block;font-size:64px;line-height:1;letter-spacing:-.03em}
.score span{color:var(--muted)}
.score .band{color:#fff}
.band{display:inline-block;margin-top:10px;padding:3px 12px;border-radius:99px;color:#fff;font-weight:600;font-size:14px}
.s-ok{background:var(--ok)}.s-fair{background:var(--fair)}.s-risk{background:var(--risk)}.s-crit{background:var(--bad)}
.start{margin:0;padding-left:20px}
.areas{list-style:none;margin:12px 0 0;padding:0}
.areas li{display:grid;grid-template-columns:minmax(150px,230px) 1fr 44px;gap:12px;align-items:center;padding:7px 0}
.track{height:12px;background:var(--bar);border-radius:6px;overflow:hidden}
.track i{display:block;height:100%;border-radius:6px}
.areas b{text-align:right;font-variant-numeric:tabular-nums}
.action{margin:12px 0;padding:16px 18px;background:var(--panel);border:1px solid var(--line);
 border-left:6px solid var(--line);border-radius:8px}
.action.High{border-left-color:var(--bad)}.action.Medium{border-left-color:var(--risk)}.action.Low{border-left-color:var(--fair)}
.action .head{display:flex;gap:12px;justify-content:space-between;align-items:baseline;margin-bottom:6px}
.tag{flex:none;padding:1px 10px;border-radius:99px;font-size:13px;font-weight:600;color:#fff}
.tag.High{background:var(--bad)}.tag.Medium{background:var(--risk)}.tag.Low{background:var(--fair)}
.action p{margin:0 0 6px}
.meta{color:var(--muted);font-size:14px}
table{width:100%;border-collapse:collapse;background:var(--panel);font-size:14px}
th,td{padding:8px 10px;text-align:left;vertical-align:top;border-top:1px solid var(--line)}
th{color:var(--muted);font-weight:600}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px}
ul.good{padding-left:20px}
.foot{margin-top:40px;color:var(--muted);font-size:14px}
.poster{page-break-before:always;margin-top:48px;padding:32px;border:3px solid var(--ink);border-radius:12px;background:#fff}
.poster h2{margin:0 0 16px;font-size:30px}.poster li{font-size:24px;line-height:1.3;margin:0 0 14px}
@media (max-width:640px){.summary{grid-template-columns:1fr}.areas li{grid-template-columns:1fr 1fr 40px}}
@media print{body{background:#fff}main{padding:0}.action,.summary{break-inside:avoid}a{color:inherit}}
"""


def page(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{esc(title)}</title><style>{CSS}</style></head><body><main>{body}</main></body></html>"
    )


def band_class(score: int) -> str:
    return "s-ok" if score >= 80 else "s-fair" if score >= 60 else "s-risk" if score >= 40 else "s-crit"


def _bar_colour(score: int) -> str:
    return {"s-ok": "var(--ok)", "s-fair": "var(--fair)", "s-risk": "var(--risk)", "s-crit": "var(--bad)"}[band_class(score)]


def summary_text(a: Assessment) -> str:
    areas = sorted(a.domain_scores().items(), key=lambda kv: kv[1])
    weakest = [a.bank.domains[d]["name"].lower() for d, _ in areas[:2]]
    plan = a.plan()
    urgent = len(plan["fix_first"])
    quick = len(plan["fix_first"]) + len(plan["this_week"])
    parts = [f"{esc(a.business.name)} scores <strong>{a.overall} out of 100</strong>: {esc(a.band.lower())}."]
    if weakest and a.overall < 100:
        parts.append(f"The weakest areas are {weakest[0]}" + (f", then {weakest[1]}." if len(weakest) > 1 else "."))
    if urgent:
        parts.append(f"{urgent} gap{'s are' if urgent != 1 else ' is'} rated high risk and should be fixed first.")
    if quick:
        parts.append(f"{quick} actions are high priority or quick wins, so most of the danger can be removed fast.")
    if not a.gaps():
        parts = [f"{esc(a.business.name)} has no gaps in this assessment. Keep it up and repeat it every six months."]
    return " ".join(parts)


def _action_card(f: Finding) -> str:
    q = f.question
    unsure = (
        '<p class="meta"><strong>You were not sure about this one.</strong> Find out first, then act.</p>'
        if f.answer == "unsure" else ""
    )
    policy = (
        f' Template: <a href="policies/{esc(q.policy)}.html">{esc(TITLES[q.policy])}</a>.' if q.policy else ""
    )
    return (
        f'<article class="action {f.level}"><div class="head"><h3>{esc(q.title)}</h3>'
        f'<span class="tag {f.level}">{f.level} risk</span></div>'
        f"<p>{esc(q.fix)}</p>"
        f"<p><strong>Why it matters.</strong> {esc(q.why)}</p>{unsure}"
        f'<p class="meta">You answered: {ANSWER_LABEL[f.answer]}. Effort: {esc(EFFORT_LABEL[q.effort])}.{policy}</p>'
        "</article>"
    )


def build_report(a: Assessment) -> str:
    b = a.business
    sector = a.bank.sectors[b.sector]["label"]
    plan = a.plan()
    ordered = a.ordered_actions()

    start = "".join(f"<li>{esc(f.question.title)}</li>" for f in ordered[:3]) or "<li>Nothing urgent.</li>"
    areas = "".join(
        f'<li><span>{esc(a.bank.domains[d]["name"])}</span>'
        f'<span class="track"><i style="width:{s}%;background:{_bar_colour(s)}"></i></span><b>{s}</b></li>'
        for d, s in sorted(a.domain_scores().items(), key=lambda kv: kv[1])
    )

    sections = []
    for key, label, blurb in PHASES:
        if plan[key]:
            cards = "".join(_action_card(f) for f in plan[key])
            sections.append(f"<h2>{esc(label)}</h2><p class=\"sub\">{esc(blurb)}</p>{cards}")

    register = "".join(
        f"<tr><td>{esc(f.question.id)}</td><td>{esc(a.bank.domains[f.question.domain]['name'])}</td>"
        f"<td>{esc(f.question.title)}</td><td>{ANSWER_LABEL[f.answer]}</td>"
        f'<td><span class="tag {f.level}">{f.level}</span> {f.risk:.0f}</td></tr>'
        for f in sorted(a.gaps(), key=lambda f: -f.risk)
    )
    good = "".join(f"<li>{esc(f.question.title)}</li>" for f in a.strengths())
    policies = "".join(f'<li><a href="policies/{p}.html">{esc(TITLES[p])}</a></li>' for p in a.policies_needed())
    skipped = ""
    if a.unanswered:
        skipped = f'<p class="meta">{len(a.unanswered)} question(s) were left unanswered and are treated as "not sure".</p>'

    body = f"""
<h1>Cyber-health report</h1>
<p class="sub">{esc(b.name)}, {esc(sector.lower())}, {b.staff} {"person" if b.staff == 1 else "people"}. Assessed on {esc(a.on)}.</p>
<section class="summary">
  <div class="score"><b>{a.overall}</b><span>out of 100</span><br><span class="band {band_class(a.overall)}">{esc(a.band)}</span></div>
  <div><p>{summary_text(a)}</p><p><strong>Start here:</strong></p><ol class="start">{start}</ol></div>
</section>
{skipped}
<h2>How each area scores</h2>
<ul class="areas">{areas}</ul>
<h2 style="margin-top:48px">Your action plan</h2>
<p class="sub">Ordered by risk, with high-risk gaps first and quick wins before big projects. Every action has a matching template or checklist where one helps.</p>
{"".join(sections) or "<p>No actions needed.</p>"}
<h2>Risk register</h2>
<div class="wrap"><table><thead><tr><th>Ref</th><th>Area</th><th>Control</th><th>You said</th><th>Risk</th></tr></thead><tbody>{register}</tbody></table></div>
<h2>What you are already doing well</h2>
{"<ul class='good'>" + good + "</ul>" if good else "<p>Nothing yet. Everyone starts somewhere, and the first quick wins make a big difference.</p>"}
<h2>Policy templates for you</h2>
<p class="sub">Filled in with your business details. Print them, fill the blanks, and share them with staff.</p>
<ul class="good">{policies}</ul>
<p>The staff session plan is in <a href="staff-briefing.html">staff-briefing.html</a>. The same plan as a tracking sheet is in <code>action-plan.csv</code>.</p>
<p class="foot">This is a self-assessment based on the answers given. It is not an audit or a penetration test, and a high score does not guarantee safety. Scores compare how well common, well-understood controls are in place, weighted for the type of business. Repeat the assessment every six months to track progress.</p>
"""
    return page(f"Cyber-health report: {b.name}", body)


def build_csv(a: Assessment) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["phase", "ref", "area", "action", "why", "risk_level", "risk_score", "effort", "you_said", "owner", "due_date", "status"])
    labels = {k: label for k, label, _ in PHASES}
    for f in a.ordered_actions():
        q = f.question
        w.writerow([
            labels[f.phase], q.id, a.bank.domains[q.domain]["name"], q.fix, q.why, f.level, f"{f.risk:.1f}",
            EFFORT_LABEL[q.effort], ANSWER_LABEL[f.answer], "", "", "To do",
        ])
    return out.getvalue()
