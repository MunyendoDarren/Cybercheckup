import csv
import json
import re

from cybercheckup import cli
from cybercheckup.build import write_all
from cybercheckup.model import DATA, load_assessment, load_bank, assess, make_business

BANK = load_bank()
EVIL = '<script>alert(1)</script> & "Co"'


def evil_assessment():
    b = make_business(BANK, {"name": EVIL, "owner": "<img src=x onerror=alert(2)>", "sector": "clinic", "staff": 3})
    return assess(BANK, b, {})


def test_demo_writes_every_deliverable(tmp_path):
    a = load_assessment(DATA / "demo.json", BANK)
    files = write_all(a, tmp_path)
    for name in ["report.html", "action-plan.csv", "assessment.json", "staff-briefing.html", "staff-briefing.md",
                 "policies/incident-response.html", "policies/password.md"]:
        assert (tmp_path / name).is_file(), name
    rows = list(csv.DictReader((tmp_path / "action-plan.csv").open(encoding="utf-8")))
    assert rows and rows[0]["phase"] == "Fix first"
    saved = json.loads((tmp_path / "assessment.json").read_text(encoding="utf-8"))
    assert saved["result"]["overall"] == a.overall


def test_every_linked_policy_exists(tmp_path):
    a = load_assessment(DATA / "demo.json", BANK)
    write_all(a, tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    for href in set(re.findall(r'href="([^"]+)"', html)):
        assert (tmp_path / href).is_file(), href


def test_untrusted_business_details_cannot_inject_html(tmp_path):
    write_all(evil_assessment(), tmp_path)
    for path in tmp_path.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert "<script>alert(1)" not in text, path
        assert "<img src=x" not in text, path


def test_reports_make_no_network_requests(tmp_path):
    write_all(load_assessment(DATA / "demo.json", BANK), tmp_path)
    for path in tmp_path.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r'(src|href)="https?://', text), path
        assert "<link" not in text and "<script" not in text, path


def test_placeholders_are_all_filled(tmp_path):
    write_all(load_assessment(DATA / "demo.json", BANK), tmp_path)
    for path in (tmp_path / "policies").glob("*.md"):
        assert "{{" not in path.read_text(encoding="utf-8"), path


def test_briefing_uses_the_businesss_own_gaps(tmp_path):
    a = load_assessment(DATA / "demo.json", BANK)
    md = (write_all(a, tmp_path) and (tmp_path / "staff-briefing.md").read_text(encoding="utf-8"))
    assert "Amani Beauty Salon" in md and "Instagram" in md  # salon scenario
    assert "Never pay to new details" in md  # PAY-01 is a gap in the demo


def test_cli_assess_from_file_and_compare(tmp_path, capsys):
    out = tmp_path / "out"
    assert cli.main(["assess", "--answers", str(DATA / "demo.json"), "--out", str(out)]) == 0
    better = json.loads((DATA / "demo.json").read_text(encoding="utf-8"))
    better["answers"]["ACC-02"] = "yes"
    better["answers"]["BAK-01"] = "yes"
    better["date"] = "2027-05-14"
    newer = tmp_path / "newer.json"
    newer.write_text(json.dumps(better), encoding="utf-8")
    assert cli.main(["compare", str(out / "assessment.json"), str(newer)]) == 0
    text = capsys.readouterr().out
    assert "Fixed since last time" in text and "Regular backups" in text


def test_cli_reports_bad_input_without_a_traceback(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"business": {"name": "X", "sector": "shop", "staff": 2}, "answers": {"ACC-01": "maybe"}}))
    assert cli.main(["assess", "--answers", str(bad), "--out", str(tmp_path / "o")]) == 2
    assert "error:" in capsys.readouterr().err


def test_interactive_wizard(tmp_path, monkeypatch):
    typed = iter(["Mama Mboga Shop", "Grace", "1", "3"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(typed, "y"))
    out = tmp_path / "wizard"
    assert cli.main(["assess", "--out", str(out)]) == 0
    saved = json.loads((out / "assessment.json").read_text(encoding="utf-8"))
    assert saved["business"]["sector"] == "shop" and saved["result"]["overall"] == 100
