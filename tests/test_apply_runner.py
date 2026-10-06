from pathlib import Path

import pytest
from apply_helpers import FakePage

from src.apply.registry import family_for
from src.apply.runner import (
    build_form_plan,
    fill_form,
    resolve_ats_url,
    run_application,
)
from src.scrapers.base import JobPost

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
GREENHOUSE_URL = "https://job-boards.greenhouse.io/acme/jobs/123"

FULL_PROFILE = {
    "name": "José E. Jiménez",
    "email": "jose@example.com",
    "location": "Caracas, Venezuela",
    "linkedin": "https://linkedin.com/in/jose",
    "github": "https://github.com/jose",
    "phone": "+58 412 000 0000",
}
NO_PHONE_PROFILE = {k: v for k, v in FULL_PROFILE.items() if k != "phone"}


def _job(url=GREENHOUSE_URL):
    return JobPost(
        title="QA Automation Engineer",
        company="Acme",
        location="Remote",
        description="Playwright",
        url=url,
        apply_url=url,
        source="Test",
    )


def _no_network(url):
    return url


def test_plan_fills_only_profile_data():
    family = family_for(GREENHOUSE_URL)
    plan = build_form_plan(family, FULL_PROFILE)
    assert plan.missing == []
    assert plan.values["#first_name"] == "José"
    assert plan.values["#last_name"] == "E. Jiménez"
    assert plan.values["#email"] == "jose@example.com"
    assert plan.values["#phone"] == "+58 412 000 0000"
    assert plan.values["#candidate-location"] == "Caracas, Venezuela"
    assert "cv_file" not in str(plan.files)


def test_plan_reports_missing_phone():
    family = family_for(GREENHOUSE_URL)
    plan = build_form_plan(family, NO_PHONE_PROFILE)
    assert plan.missing == ["phone"]
    assert "#phone" not in plan.values


def test_empty_apply_url_short_circuits():
    """Caso límite de la spec: sin apply_url no se intenta nada."""
    job = _job(url="https://example.com/job/9")
    job.apply_url = ""
    result = run_application(
        job, FULL_PROFILE, FakePage("<html></html>"), resolver=_no_network
    )
    assert result.outcome == "dominio_no_soportado"
    assert result.detail == "sin_apply_url"


def test_unknown_domain_short_circuits():
    page = FakePage("<html></html>")
    job = _job(url="https://example.com/careers/1")
    result = run_application(job, FULL_PROFILE, page, resolver=_no_network)
    assert result.outcome == "dominio_no_soportado"
    assert result.detail == "dominio_no_registrado"
    assert page.calls == []


def test_blocked_family_detail():
    """RF-7: ashby registrada pero bloqueada por CAPTCHA visible."""
    page = FakePage("<html></html>")
    job = _job(url="https://jobs.ashbyhq.com/acme/uuid-1")
    result = run_application(job, FULL_PROFILE, page, resolver=_no_network)
    assert result.outcome == "dominio_no_soportado"
    assert result.detail == "captcha_visible"
    assert page.calls == []


def test_dato_faltante_before_navigation():
    page = FakePage("<html></html>")
    result = run_application(_job(), NO_PHONE_PROFILE, page, resolver=_no_network)
    assert result.outcome == "dato_faltante"
    assert result.detail == "phone"
    assert page.calls == []


def test_happy_path_against_fixture():
    html = (FIXTURES / "ats_greenhouse_min.html").read_text(encoding="utf-8")
    page = FakePage(html)
    result = run_application(_job(), FULL_PROFILE, page, resolver=_no_network)
    assert result.outcome == "enviado"
    assert result.family == "greenhouse"
    assert page.filled["#first_name"] == "José"
    assert page.filled["#email"] == "jose@example.com"
    clicks = [c for c in page.calls if c[0] == "click"]
    assert len(clicks) == 1, "RF-6: un solo intento"
    assert result.confirmation_url.endswith("?application=ok")
    assert "application received" in result.evidence


def test_no_confirmation_is_single_error():
    """RF-6: sin confirmación → error, sin reintento."""
    html = (FIXTURES / "ats_greenhouse_min.html").read_text(encoding="utf-8")
    page = FakePage(html, confirm_on_submit=False)
    result = run_application(_job(), FULL_PROFILE, page, resolver=_no_network)
    assert result.outcome == "error"
    assert len([c for c in page.calls if c[0] == "click"]) == 1


def test_goto_receives_budgeted_timeout():
    """RNF-1: el timeout pasado al navegador nunca supera 90 s."""
    html = (FIXTURES / "ats_greenhouse_min.html").read_text(encoding="utf-8")
    page = FakePage(html)
    run_application(_job(), FULL_PROFILE, page, resolver=_no_network)
    goto = next(c for c in page.calls if c[0] == "goto")
    assert goto[2] is not None and goto[2] <= 90_000


def test_real_fixture_gates():
    """Contra el fixture real de Greenhouse: primero el teléfono (P6) y,
    con teléfono, las preguntas personalizadas obligatorias."""
    html = (FIXTURES / "ats_greenhouse.html").read_text(encoding="utf-8")
    page = FakePage(html)
    result = run_application(_job(), NO_PHONE_PROFILE, page, resolver=_no_network)
    assert result.outcome == "dato_faltante"
    assert result.detail == "phone"
    assert page.calls == []

    page = FakePage(html)
    result = run_application(_job(), FULL_PROFILE, page, resolver=_no_network)
    assert result.outcome == "dato_faltante"
    assert result.detail == "custom_questions"


def test_resolve_ats_url_from_outbound_link():
    def fetch(url):
        return url, '<a href="https://job-boards.greenhouse.io/acme/jobs/9">Apply</a>'

    assert resolve_ats_url("https://board.example.com/job/1", fetch=fetch) == (
        "https://job-boards.greenhouse.io/acme/jobs/9"
    )
    direct = resolve_ats_url(GREENHOUSE_URL, fetch=lambda u: pytest.fail("sin fetch directo"))
    assert direct == GREENHOUSE_URL


def test_real_browser_fills_fixture():
    """RNF-4: selectores comprobados con navegador real contra fixture local."""
    playwright = pytest.importorskip("playwright.sync_api")
    html = (FIXTURES / "ats_greenhouse_min.html").read_text(encoding="utf-8")
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"chromium no disponible: {exc}")
        page = browser.new_page()
        page.set_content(html)
        family = family_for(GREENHOUSE_URL)
        plan = build_form_plan(family, FULL_PROFILE)
        fill_form(page, family, plan)
        assert page.input_value("#first_name") == "José"
        assert page.input_value("#last_name") == "E. Jiménez"
        assert page.input_value("#email") == "jose@example.com"
        browser.close()
