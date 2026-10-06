from pathlib import Path

from bs4 import BeautifulSoup

from src.apply.registry import FAMILIES, family_for, submittable_family

FIXTURES = Path(__file__).resolve().parent.parent

GREENHOUSE_URL = "https://job-boards.greenhouse.io/nationalpublicradioinc/jobs/4740242005"
ASHBY_URL = "https://jobs.ashbyhq.com/stable/17ed97f1-7418-4bd0-9a83-2eaccb0212c7"


def _fixture(family):
    return BeautifulSoup((FIXTURES / family.fixture).read_text(encoding="utf-8"), "html.parser")


def test_family_for_matches_registered_hosts():
    assert family_for(GREENHOUSE_URL).name == "greenhouse"
    assert family_for("https://boards.greenhouse.io/acme/jobs/1").name == "greenhouse"
    assert family_for(ASHBY_URL).name == "ashby"
    assert family_for("https://jobs.lever.co/acme/abc").name == "lever"
    assert family_for("https://apply.workable.com/acme/j/abc").name == "workable"


def test_unknown_domain_returns_none():
    """RF-5: dominio sin registro no produce familia (nunca adivina)."""
    assert family_for("https://example.com/careers/1") is None
    assert family_for("") is None
    assert family_for("careers.company.com/jobs/1") is None


def test_only_greenhouse_is_submittable():
    """RF-5 + RF-7: solo greenhouse pasa el gate; ashby bloqueada por CAPTCHA
    visible; lever/workable pendientes de captura."""
    assert submittable_family(GREENHOUSE_URL).name == "greenhouse"
    assert submittable_family(ASHBY_URL) is None
    assert submittable_family("https://jobs.lever.co/acme/abc") is None
    assert submittable_family("https://apply.workable.com/acme/j/abc") is None
    assert submittable_family("https://example.com/job") is None


def test_greenhouse_selectors_exist_in_fixture():
    family = next(f for f in FAMILIES if f.name == "greenhouse")
    assert family.fixture is not None
    soup = _fixture(family)
    assert soup.select_one(family.form_selector) is not None
    for key, selector in family.field_selectors.items():
        assert soup.select_one(selector) is not None, f"selector perdido: {key}"
    assert soup.select_one(family.submit_selector) is not None
    assert soup.select_one(family.custom_question_selector) is not None


def test_ashby_selectors_exist_in_fixture_but_blocked():
    family = next(f for f in FAMILIES if f.name == "ashby")
    assert family.fixture is not None
    soup = _fixture(family)
    for key, selector in family.field_selectors.items():
        assert soup.select_one(selector) is not None, f"selector perdido: {key}"
    assert soup.select_one(family.submit_selector) is not None
    assert family.captcha == "interactive"
    assert family.blocked_reason == "captcha_visible"
    assert not family.can_submit


def test_pending_families_have_no_selectors():
    """RF-5: familias sin captura quedan marcadas y no aportan selectores."""
    for name in ("lever", "workable"):
        family = next(f for f in FAMILIES if f.name == name)
        assert not family.validated
        assert family.blocked_reason == "pendiente_captura"
        assert family.form_selector is None
        assert not family.can_submit
