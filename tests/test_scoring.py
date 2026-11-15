import pytest

from cybercheckup.model import assess, load_bank, make_business, applicable_questions

BANK = load_bank()


def biz(sector="other", staff=5, name="Test Co"):
    return make_business(BANK, {"name": name, "owner": "Sam", "sector": sector, "staff": staff})


def all_answers(value, sector="other", staff=5):
    return {q.id: value for q in applicable_questions(BANK, biz(sector, staff))}


def test_perfect_and_worst_scores():
    assert assess(BANK, biz(), all_answers("yes")).overall == 100
    assert assess(BANK, biz(), all_answers("no")).overall == 0
    assert assess(BANK, biz(), all_answers("partly")).overall == 50


def test_unsure_counts_as_no_and_skip_is_excluded():
    assert assess(BANK, biz(), all_answers("unsure")).overall == 0
    answers = all_answers("yes")
    answers["ACC-01"] = "skip"
    a = assess(BANK, biz(), answers)
    assert "ACC-01" not in {f.question.id for f in a.findings}
    assert a.overall == 100


def test_unanswered_questions_are_flagged_and_treated_as_unsure():
    a = assess(BANK, biz(), {})
    assert len(a.unanswered) == len(a.findings) and a.overall == 0


def test_small_and_sector_specific_questions_apply_correctly():
    solo = {q.id for q in applicable_questions(BANK, biz(staff=1))}
    team = {q.id for q in applicable_questions(BANK, biz(staff=5))}
    assert "PPL-02" not in solo and "PPL-02" in team
    assert "DAT-03" not in {q.id for q in applicable_questions(BANK, biz("shop"))}
    assert "DAT-03" in {q.id for q in applicable_questions(BANK, biz("clinic"))}
    assert "PAY-05" in {q.id for q in applicable_questions(BANK, biz("shop"))}


def test_sector_weights_raise_the_priority_of_the_same_gap():
    answers = {"DAT-02": "no"}
    base = assess(BANK, biz("other"), answers).findings
    clinic = assess(BANK, biz("clinic"), answers).findings
    risk = lambda fs: next(f.risk for f in fs if f.question.id == "DAT-02")
    assert risk(clinic) == pytest.approx(risk(base) * 1.5)


def test_plan_puts_critical_first_and_quick_wins_before_projects():
    a = assess(BANK, biz("shop"), all_answers("no", "shop"))
    plan = a.plan()
    assert plan["fix_first"], "a business with no controls must have critical items"
    assert all(f.risk >= 18 for f in plan["fix_first"])
    assert all(f.question.effort == 1 for f in plan["this_week"])
    assert all(f.question.effort == 2 for f in plan["this_month"])
    for items in plan.values():
        risks = [f.risk for f in items]
        assert risks == sorted(risks, reverse=True)


def test_invalid_input_is_rejected():
    with pytest.raises(ValueError):
        assess(BANK, biz(), {"ACC-01": "maybe"})
    with pytest.raises(ValueError):
        make_business(BANK, {"name": "", "sector": "shop", "staff": 3})
    with pytest.raises(ValueError):
        make_business(BANK, {"name": "X", "sector": "spaceship", "staff": 3})
    with pytest.raises(ValueError):
        make_business(BANK, {"name": "X", "sector": "shop", "staff": 0})


def test_unknown_question_ids_are_ignored():
    assert assess(BANK, biz(), {"OLD-99": "yes"}).overall == 0
