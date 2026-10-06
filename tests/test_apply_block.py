import json
from datetime import datetime, timezone
from pathlib import Path

from apply_helpers import FakePage

from src.apply.batch import run_batch
from src.apply.ledger import ApplicationLedger
from src.apply.maintenance import FamilyStatus
from src.apply.runner import detect_block, run_application
from src.scrapers.base import JobPost

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
GREENHOUSE_URL = "https://job-boards.greenhouse.io/acme/jobs/111"

PROFILE = {
    "name": "José E. Jiménez",
    "email": "jose@example.com",
    "location": "Caracas, Venezuela",
    "phone": "+58 412 000 0000",
}
MIN_FORM = (FIXTURES / "ats_greenhouse_min.html").read_text(encoding="utf-8")
CAPTCHA_FORM = MIN_FORM.replace(
    "</body>",
    '<iframe title="reCAPTCHA" width="256" height="60"></iframe></body>',
)
ASHBY_FORM = (FIXTURES / "ats_ashby_form.html").read_text(encoding="utf-8")
LOGIN_URL = "https://job-boards.greenhouse.io/login?from=apply"


def _job(n=1):
    return JobPost(
        title=f"QA Automation Engineer {n}",
        company="Acme",
        location="Remote",
        description="Playwright",
        url=f"{GREENHOUSE_URL}?ref={n}",
        apply_url=GREENHOUSE_URL,
        source="Test",
    )


def test_detect_captcha_on_visible_widget():
    """RF-7: el widget interactivo de Ashby (fixture) se detecta."""
    page = FakePage(ASHBY_FORM)
    assert detect_block(page) == "captcha"


def test_invisible_captcha_is_ignored():
    """Decision 2026-10-06: tokens invisibles no son un desafío."""
    html = (
        '<html><body><div style="display: none;">'
        '<iframe title="reCAPTCHA" width="0" height="0"></iframe>'
        "</div></body></html>"
    )
    assert detect_block(FakePage(html)) is None


def test_detect_login_by_url():
    page = FakePage(MIN_FORM)
    page.url = LOGIN_URL
    assert detect_block(page) == "login"


def test_run_application_returns_bloqueo_on_captcha():
    page = FakePage(CAPTCHA_FORM)
    result = run_application(_job(), PROFILE, page, resolver=lambda u: u)
    assert result.outcome == "bloqueo"
    assert result.detail == "captcha"


def test_run_application_returns_bloqueo_on_login():
    page = FakePage(MIN_FORM, redirect_url=LOGIN_URL)
    result = run_application(_job(), PROFILE, page, resolver=lambda u: u)
    assert result.outcome == "bloqueo"
    assert result.detail == "login"


def test_captcha_stops_whole_batch(tmp_path):
    """RF-7: el CAPTCHA interactivo detiene el lote de la sesión."""
    ledger = ApplicationLedger(tmp_path / "applications.json")
    status = FamilyStatus(tmp_path / "family_status.json")
    report = run_batch(
        [_job(1), _job(2), _job(3)],
        PROFILE,
        ledger=ledger,
        page_factory=lambda job: FakePage(CAPTCHA_FORM),
        daily_limit=5,
        resolver=lambda u: u,
        status=status,
        now=datetime.now(timezone.utc),
    )
    assert report.stopped_reason == "captcha_detectado"
    assert report.processed == 1
    entries = ledger.load()
    assert len(entries) == 1
    assert entries[0]["outcome"] == "bloqueo"
    assert entries[0]["detail"] == "captcha"


def test_login_on_first_offer_stops_batch(tmp_path):
    """Caso limite (spec): control de acceso en la primera oferta →
    se detiene el modo auto de la sesión."""
    ledger = ApplicationLedger(tmp_path / "applications.json")
    status = FamilyStatus(tmp_path / "family_status.json")
    report = run_batch(
        [_job(1), _job(2)],
        PROFILE,
        ledger=ledger,
        page_factory=lambda job: FakePage(MIN_FORM, redirect_url=LOGIN_URL),
        daily_limit=5,
        resolver=lambda u: u,
        status=status,
    )
    assert report.stopped_reason == "login_primera_oferta"
    assert report.processed == 1


def test_login_after_first_offer_only_fails_that_attempt(tmp_path):
    ledger = ApplicationLedger(tmp_path / "applications.json")
    status = FamilyStatus(tmp_path / "family_status.json")
    pages = iter(
        [
            FakePage(MIN_FORM),
            FakePage(MIN_FORM, redirect_url=LOGIN_URL),
        ]
    )
    report = run_batch(
        [_job(1), _job(2)],
        PROFILE,
        ledger=ledger,
        page_factory=lambda job: next(pages),
        daily_limit=5,
        resolver=lambda u: u,
        status=status,
    )
    assert report.stopped_reason is None
    assert report.processed == 2
    assert report.sent == 1
    assert report.results[1][1].outcome == "bloqueo"
    assert report.results[1][1].detail == "login"


def test_selector_failure_demotes_family(tmp_path):
    """RF-6 + plan fase 2: selector caído → validated:false en disco."""
    status = FamilyStatus(tmp_path / "family_status.json")
    page = FakePage("<html><body><p>pagina sin formulario</p></body></html>")
    result = run_application(
        _job(),
        PROFILE,
        page,
        resolver=lambda u: u,
        status=status,
    )
    assert result.outcome == "error"
    assert result.detail == "selector_ausente"
    assert status.is_active("greenhouse") is False
    data = json.loads((tmp_path / "family_status.json").read_text(encoding="utf-8"))
    assert data["greenhouse"]["validated"] is False
    assert data["greenhouse"]["reason"] == "selector_ausente"


def test_demoted_family_is_blocked_before_navigation(tmp_path):
    status = FamilyStatus(tmp_path / "family_status.json")
    status.demote("greenhouse", "selector_ausente")
    page = FakePage(MIN_FORM)
    result = run_application(
        _job(),
        PROFILE,
        page,
        resolver=lambda u: u,
        status=status,
    )
    assert result.outcome == "dominio_no_soportado"
    assert result.detail == "requiere_mantenimiento"
    assert page.calls == []


def test_post_submit_login_is_not_counted_as_sent(tmp_path):
    """RF-7: si la confirmación cae en login, no se afirma envío."""
    status = FamilyStatus(tmp_path / "family_status.json")
    page = FakePage(MIN_FORM, confirm_to=LOGIN_URL)
    result = run_application(
        _job(),
        PROFILE,
        page,
        resolver=lambda u: u,
        status=status,
    )
    assert result.outcome == "bloqueo"
    assert result.detail == "login"


def test_family_status_persistence(tmp_path):
    status = FamilyStatus(tmp_path / "family_status.json")
    assert status.is_active("greenhouse") is True
    status.demote("greenhouse", "selector_ausente")
    reloaded = FamilyStatus(tmp_path / "family_status.json")
    assert reloaded.is_active("greenhouse") is False
    assert reloaded.is_active("lever") is False
