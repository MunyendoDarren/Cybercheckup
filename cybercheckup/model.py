"""Question bank, scoring and prioritisation.

Risk of one gap   = likelihood x impact x sector weight x gap
Gap               = 1 - answer value   (yes 0, partly 0.5, no/unsure 1)
Area / overall    = 100 x (1 - sum of risks / sum of maximum risks)

See docs/METHODOLOGY.md for the reasoning.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from importlib import resources
from pathlib import Path

import yaml

DATA = resources.files("cybercheckup") / "data"

ANSWER_VALUE = {"yes": 1.0, "partly": 0.5, "no": 0.0, "unsure": 0.0}
VALID_ANSWERS = set(ANSWER_VALUE) | {"skip"}
ANSWER_LABEL = {"yes": "Yes", "partly": "Partly", "no": "No", "unsure": "Not sure", "skip": "Not applicable"}

CRITICAL_RISK = 18.0  # at or above: "fix first", whatever the effort
MEDIUM_RISK = 9.0

EFFORT_LABEL = {
    1: "Under an hour, usually free",
    2: "About a day, or a small cost",
    3: "A project: plan time and budget",
}
PHASES = [
    ("fix_first", "Fix first", "The biggest risks. Do these before anything else."),
    ("this_week", "This week", "Quick wins: under an hour each and usually free."),
    ("this_month", "This month", "Worth a day of effort or a small cost."),
    ("this_quarter", "This quarter", "Larger jobs. Plan time and budget."),
]
BANDS = [(80, "Healthy"), (60, "Fair"), (40, "At risk"), (0, "Needs urgent attention")]


@dataclass(frozen=True)
class Question:
    id: str
    domain: str
    title: str
    q: str
    why: str
    fix: str
    impact: int
    likelihood: int
    effort: int
    policy: str | None = None
    profiles: tuple[str, ...] | None = None
    min_staff: int = 1
    rule: str | None = None


@dataclass(frozen=True)
class Bank:
    domains: dict
    questions: tuple[Question, ...]
    sectors: dict


@dataclass(frozen=True)
class Business:
    name: str
    owner: str
    sector: str
    staff: int


@dataclass(frozen=True)
class Finding:
    question: Question
    answer: str
    gap: float
    risk: float
    max_risk: float

    @property
    def level(self) -> str:
        if self.risk >= CRITICAL_RISK:
            return "High"
        return "Medium" if self.risk >= MEDIUM_RISK else "Low"

    @property
    def phase(self) -> str:
        if self.risk >= CRITICAL_RISK:
            return "fix_first"
        return PHASES[self.question.effort][0]


@lru_cache(maxsize=1)
def load_bank() -> Bank:
    raw = yaml.safe_load((DATA / "questions.yaml").read_text(encoding="utf-8"))
    prof = yaml.safe_load((DATA / "profiles.yaml").read_text(encoding="utf-8"))
    questions = []
    for item in raw["questions"]:
        item = dict(item)
        if "profiles" in item:
            item["profiles"] = tuple(item["profiles"])
        questions.append(Question(**item))
    return Bank(raw["domains"], tuple(questions), prof["sectors"])


def applies(q: Question, business: Business) -> bool:
    if business.staff < q.min_staff:
        return False
    return q.profiles is None or business.sector in q.profiles


def applicable_questions(bank: Bank, business: Business) -> list[Question]:
    return [q for q in bank.questions if applies(q, business)]


def make_business(bank: Bank, data: dict) -> Business:
    name = str(data.get("name", "")).strip()
    if not name or len(name) > 80:
        raise ValueError("business name is required (80 characters at most)")
    sector = str(data.get("sector", "other")).strip().lower()
    if sector not in bank.sectors:
        raise ValueError(f"unknown sector '{sector}'. Choose one of: {', '.join(bank.sectors)}")
    try:
        staff = int(data.get("staff", 1))
    except (TypeError, ValueError):
        raise ValueError("staff must be a whole number") from None
    if not 1 <= staff <= 10_000:
        raise ValueError("staff must be between 1 and 10000")
    owner = str(data.get("owner", "")).strip()[:80] or "the owner"
    return Business(name, owner, sector, staff)


def normalise_answers(bank: Bank, answers: dict) -> dict[str, str]:
    known = {q.id for q in bank.questions}
    clean = {}
    for key, value in answers.items():
        if key not in known:
            continue  # ignore ids from other versions of the bank
        value = str(value).strip().lower()
        if value not in VALID_ANSWERS:
            raise ValueError(f"{key}: '{value}' is not one of {sorted(VALID_ANSWERS)}")
        clean[key] = value
    return clean


@dataclass
class Assessment:
    business: Business
    on: str
    answers: dict
    findings: list[Finding]
    unanswered: list[str]
    bank: Bank

    # ---- scores
    @staticmethod
    def _score(findings: list[Finding]) -> int:
        total = sum(f.max_risk for f in findings)
        if not total:
            return 100
        return round(100 * (1 - sum(f.risk for f in findings) / total))

    @property
    def overall(self) -> int:
        return self._score(self.findings)

    @property
    def band(self) -> str:
        return band_for(self.overall)

    def domain_scores(self) -> dict[str, int]:
        out = {}
        for dom in self.bank.domains:
            fs = [f for f in self.findings if f.question.domain == dom]
            if fs:
                out[dom] = self._score(fs)
        return out

    # ---- plan
    def gaps(self) -> list[Finding]:
        return [f for f in self.findings if f.gap > 0]

    def strengths(self) -> list[Finding]:
        return [f for f in self.findings if f.gap == 0]

    def plan(self) -> dict[str, list[Finding]]:
        grouped = {key: [] for key, _, _ in PHASES}
        for f in self.gaps():
            grouped[f.phase].append(f)
        for items in grouped.values():
            items.sort(key=lambda f: (-f.risk, f.question.effort, f.question.id))
        return grouped

    def ordered_actions(self) -> list[Finding]:
        plan = self.plan()
        return [f for key, _, _ in PHASES for f in plan[key]]

    def policies_needed(self) -> list[str]:
        ids = {f.question.policy for f in self.gaps() if f.question.policy}
        ids.add("incident-response")
        return sorted(ids)

    def to_dict(self) -> dict:
        b = self.business
        return {
            "business": {"name": b.name, "owner": b.owner, "sector": b.sector, "staff": b.staff},
            "date": self.on,
            "answers": self.answers,
            "result": {"overall": self.overall, "band": self.band, "areas": self.domain_scores()},
        }


def band_for(score: int) -> str:
    return next(label for floor, label in BANDS if score >= floor)


def assess(bank: Bank, business: Business, answers: dict, on: str | None = None) -> Assessment:
    answers = normalise_answers(bank, answers)
    weights = bank.sectors[business.sector].get("weights", {})
    findings, unanswered = [], []
    for q in applicable_questions(bank, business):
        value = answers.get(q.id)
        if value is None:
            value = "unsure"  # an unanswered question is treated as "not sure"
            unanswered.append(q.id)
        if value == "skip":
            continue
        max_risk = q.impact * q.likelihood * weights.get(q.domain, 1.0)
        gap = 1.0 - ANSWER_VALUE[value]
        findings.append(Finding(q, value, gap, max_risk * gap, max_risk))
    return Assessment(business, on or date.today().isoformat(), answers, findings, unanswered, bank)


def load_assessment(path: str | Path, bank: Bank | None = None) -> Assessment:
    bank = bank or load_bank()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return assess(bank, make_business(bank, data.get("business", {})), data.get("answers", {}), data.get("date"))


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:50] or "business"
