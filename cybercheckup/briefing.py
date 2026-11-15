"""Staff briefing: a 30-minute session plan built from this business's own gaps."""
from __future__ import annotations

import html

from .model import Assessment

DEFAULT_RULES = [
    "Stop and check before you click, pay or reply to anything urgent or too good to be true.",
    "Never read out a PIN or one-time code to anyone.",
    "Use a different password for every account, saved in our password manager.",
    "Lock your phone and computer every time you step away.",
    "If you clicked, paid or lost something, tell the manager straight away. Reporting fast is never punished.",
]

QUIZ = [
    ("A message says you received money by mistake and asks you to send it back. What do you do?",
     "Check the balance or statement in the official app. Never send money back because of a message alone."),
    ("Someone phones, says they are from the bank, and asks for the code just sent to your phone. What do you do?",
     "Say no, hang up, and call the bank on its official number. Banks never ask for codes."),
    ("A supplier emails new bank details for the next invoice. What do you do?",
     "Call the supplier on a number we already have and confirm before paying."),
    ("You click a link, then realise it looks fake. What do you do?",
     "Tell the manager immediately and change any password you typed. Nobody is blamed for reporting."),
    ("A colleague asks to use your login 'just for today'. What do you do?",
     "Say no. Ask the manager to create them their own login."),
]


def pick_rules(a: Assessment, limit: int = 5) -> list[str]:
    rules: list[str] = []
    for f in sorted(a.gaps(), key=lambda f: -f.risk):
        rule = f.question.rule
        if rule and rule not in rules:
            rules.append(rule)
        if len(rules) == limit:
            return rules
    for rule in DEFAULT_RULES:
        if len(rules) < limit and rule not in rules:
            rules.append(rule)
    return rules


def build_markdown(a: Assessment) -> str:
    b = a.business
    sector = a.bank.sectors[b.sector]
    changes = [f"- {f.question.fix}" for f in a.ordered_actions()[:3]]
    lines = [
        f"# Staff cyber briefing: {b.name}",
        "",
        f"**Led by:** {b.owner}  ",
        f"**Date:** {a.on}  ",
        "**Length:** 30 minutes. Everyone attends, including the owner. Repeat every six months and for every new starter.",
        "",
        "## 1. Why we are doing this (3 minutes)",
        "",
        "Criminals do not only target big companies. Small businesses are attacked because they are easier. "
        "Most of the damage comes from a few simple tricks, and a few simple habits stop them. "
        "This is not about blame. It is about all of us knowing the tricks.",
        "",
        "## 2. Scams aimed at businesses like ours (7 minutes)",
        "",
        "Read each one aloud and ask: what would you do?",
        "",
        *[f"- {s}" for s in sector["scenarios"]],
        "",
        "## 3. Our five rules (10 minutes)",
        "",
        *[f"{i}. {r}" for i, r in enumerate(pick_rules(a), 1)],
        "",
        "Explain the reason behind each rule, and ask staff for examples of when it would be hard to follow.",
        "",
        "## 4. What we are changing (3 minutes)",
        "",
        "From our cyber-health assessment, these come first:",
        "",
        *(changes or ["- Keep up the good habits. No major gaps were found."]),
        "",
        "## 5. If something goes wrong (2 minutes)",
        "",
        f"Tell {b.owner} straight away. Do not delete anything and do not try to fix it quietly. "
        "Fast reporting is always rewarded and never punished. The phone numbers are on the incident response plan.",
        "",
        "## 6. Quick quiz (5 minutes)",
        "",
    ]
    for i, (question, answer) in enumerate(QUIZ, 1):
        lines += [f"{i}. {question}", f"   *Answer: {answer}*", ""]
    lines += ["## Print and pin: our five rules", "", *[f"{i}. {r}" for i, r in enumerate(pick_rules(a), 1)], ""]
    return "\n".join(lines)


def poster_html(a: Assessment) -> str:
    items = "".join(f"<li>{html.escape(r)}</li>" for r in pick_rules(a))
    return (
        f'<section class="poster"><h2>{html.escape(a.business.name)}: our five security rules</h2>'
        f"<ol>{items}</ol></section>"
    )
