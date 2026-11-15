"""Command line interface.

    cybercheckup assess                      interactive questionnaire
    cybercheckup assess --answers file.json  non-interactive (regenerates all outputs)
    cybercheckup demo                        sample salon assessment
    cybercheckup compare old.json new.json   show progress between two assessments
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from datetime import date
from pathlib import Path

from . import __version__
from .build import write_all
from .model import (
    ANSWER_LABEL, DATA, Assessment, Bank, applicable_questions, assess, load_assessment, load_bank,
    make_business, slugify,
)

KEYS = {"y": "yes", "yes": "yes", "p": "partly", "partly": "partly", "n": "no", "no": "no",
        "u": "unsure", "unsure": "unsure", "s": "skip", "skip": "skip"}
WIDTH = 78


def say(text: str = "") -> None:
    print(textwrap.fill(text, WIDTH) if text else "")


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        raise SystemExit("\nInput ended before the assessment was finished.") from None


def run_wizard(bank: Bank) -> tuple[dict, dict]:
    say("CyberCheckup: cyber-health check for small businesses")
    say("Answer in plain terms. There are no wrong answers, and nothing leaves this computer.")
    say()
    info: dict = {}
    while not info.get("name"):
        info["name"] = ask("Business name: ")
    info["owner"] = ask("Owner or manager's name: ")
    sectors = list(bank.sectors)
    say("What kind of business is it?")
    for i, key in enumerate(sectors, 1):
        print(f"  {i}. {bank.sectors[key]['label']}")
    while True:
        choice = ask(f"Choose 1-{len(sectors)}: ").lower()
        if choice.isdigit() and 1 <= int(choice) <= len(sectors):
            info["sector"] = sectors[int(choice) - 1]
            break
        if choice in sectors:
            info["sector"] = choice
            break
    while True:
        staff = ask("How many people work there, including you? ")
        if staff.isdigit() and int(staff) >= 1:
            info["staff"] = int(staff)
            break
    business = make_business(bank, info)
    questions = applicable_questions(bank, business)
    say()
    say("For each question: [y] yes  [p] partly  [n] no  [u] not sure  [s] not applicable  [?] why it matters")
    answers: dict = {}
    current_domain = None
    for i, q in enumerate(questions, 1):
        if q.domain != current_domain:
            current_domain = q.domain
            say()
            say(f"== {bank.domains[q.domain]['name']} ==")
        say()
        say(f"({i}/{len(questions)}) {q.q}")
        while True:
            raw = ask("> ").lower()
            if raw == "?":
                say(f"Why it matters: {q.why}")
            elif raw in KEYS:
                answers[q.id] = KEYS[raw]
                break
            else:
                say("Please type y, p, n, u, s or ?")
    return info, answers


def print_summary(a: Assessment, files: dict, out: Path) -> None:
    say()
    say(f"Cyber-health score for {a.business.name}: {a.overall}/100 ({a.band})")
    say()
    for key, items in a.plan().items():
        if items:
            say(f"{key.replace('_', ' ').capitalize()}: {len(items)} action(s)")
    say()
    say(f"Open {out / 'report.html'} in your browser to see the full report.")
    say("Also written: action-plan.csv, staff-briefing.html, and policy templates in the policies folder.")


def cmd_assess(args) -> int:
    bank = load_bank()
    if args.answers:
        a = load_assessment(args.answers, bank)
    else:
        info, answers = run_wizard(bank)
        a = assess(bank, make_business(bank, info), answers)
    out = Path(args.out) if args.out else Path("cybercheckup-output") / f"{slugify(a.business.name)}-{a.on}"
    files = write_all(a, out)
    print_summary(a, files, out)
    return 0


def cmd_demo(args) -> int:
    bank = load_bank()
    a = load_assessment(DATA / "demo.json", bank)
    out = Path(args.out or "cybercheckup-output/demo")
    files = write_all(a, out)
    print_summary(a, files, out)
    return 0


def cmd_compare(args) -> int:
    bank = load_bank()
    old, new = load_assessment(args.old, bank), load_assessment(args.new, bank)
    say(f"{new.business.name}: {old.on} to {new.on}")
    say(f"Overall: {old.overall} -> {new.overall} ({new.overall - old.overall:+d})")
    old_scores, new_scores = old.domain_scores(), new.domain_scores()
    for dom, score in new_scores.items():
        before = old_scores.get(dom)
        change = f"{before} -> {score} ({score - before:+d})" if before is not None else f"{score} (new)"
        print(f"  {bank.domains[dom]['name']}: {change}")
    old_gaps = {f.question.id for f in old.gaps()}
    new_gaps = {f.question.id for f in new.gaps()}
    titles = {q.id: q.title for q in bank.questions}
    fixed, opened = sorted(old_gaps - new_gaps), sorted(new_gaps - old_gaps)
    if fixed:
        say()
        say("Fixed since last time:")
        for i in fixed:
            print(f"  + {titles[i]}")
    if opened:
        say()
        say("New gaps:")
        for i in opened:
            print(f"  - {titles[i]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cybercheckup", description="Cyber-health assessment for small businesses.")
    parser.add_argument("--version", action="version", version=f"cybercheckup {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("assess", help="run the questionnaire and write the report")
    p.add_argument("--answers", help="JSON file with the business and answers (skips the questions)")
    p.add_argument("--out", help="output folder (default cybercheckup-output/<business>-<date>)")
    p.set_defaults(fn=cmd_assess)
    p = sub.add_parser("demo", help="generate a sample report for a fictional salon")
    p.add_argument("--out")
    p.set_defaults(fn=cmd_demo)
    p = sub.add_parser("compare", help="compare two saved assessments")
    p.add_argument("old")
    p.add_argument("new")
    p.set_defaults(fn=cmd_compare)
    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
