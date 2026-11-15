from cybercheckup.model import DATA, PHASES, load_bank


def test_question_bank_is_well_formed():
    bank = load_bank()
    ids = [q.id for q in bank.questions]
    assert len(ids) == len(set(ids)), "duplicate question ids"
    for q in bank.questions:
        assert q.domain in bank.domains, q.id
        assert 1 <= q.impact <= 5 and 1 <= q.likelihood <= 5 and 1 <= q.effort <= 3, q.id
        assert q.title and q.q and q.why and q.fix, q.id
        if q.policy:
            assert (DATA / "policies" / f"{q.policy}.md").is_file(), f"{q.id}: missing policy {q.policy}"
        for sector in q.profiles or ():
            assert sector in bank.sectors, f"{q.id}: unknown sector {sector}"


def test_every_domain_has_questions_and_every_sector_has_scenarios():
    bank = load_bank()
    used = {q.domain for q in bank.questions}
    assert used == set(bank.domains)
    for key, sector in bank.sectors.items():
        assert sector["label"] and len(sector["scenarios"]) >= 3, key
        for domain in sector["weights"]:
            assert domain in bank.domains, f"{key}: unknown domain {domain}"


def test_phases_cover_all_efforts():
    assert len(PHASES) == 4  # fix_first + one phase per effort level 1..3
