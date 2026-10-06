from src.config import apply_mode_from, config
from src.notifier.template import generar_html, generar_texto
from src.profile import profile
from src.scrapers.base import JobPost


def _job():
    return JobPost(
        title="QA Automation Engineer",
        company="Acme Corp",
        location="Remote",
        description="Playwright automation for a remote team",
        url="https://example.com/job/1",
        source="Test",
        match_score=80,
        cover_letter="Dear Hiring Manager,\nI am interested in this role.",
    )


def test_default_is_assist():
    """RF-1 (spec 003): default assist y valores invalidos caen a assist."""
    assert apply_mode_from("") == "assist"
    assert apply_mode_from("unknown") == "assist"
    assert apply_mode_from("AUTO ") == "auto"
    assert apply_mode_from("off") == "off"


def test_off_has_no_checklist(monkeypatch):
    monkeypatch.setattr(config, "apply_mode", "off")
    html = generar_html([_job()], "2026-10-06")
    assert "Postulacion asistida" not in html
    assert "Checklist antes de enviar" not in html
    text = generar_texto([_job()], "2026-10-06")
    assert "Postulacion asistida" not in text


def test_assist_includes_checklist_and_letter(monkeypatch):
    """RF-2 (spec 003): enlace, datos del perfil, carta y checklist por oferta."""
    monkeypatch.setattr(config, "apply_mode", "assist")
    job = _job()
    html = generar_html([job], "2026-10-06")
    assert "Postulacion asistida" in html
    assert "Checklist antes de enviar" in html
    assert (job.apply_url or job.url) in html
    assert profile.email in html
    assert "Dear Hiring Manager" in html
    assert "que la oferta sigue publicada" in html

    text = generar_texto([job], "2026-10-06")
    assert "Postulacion asistida" in text
    assert "[ ]" in text
    assert "Dear Hiring Manager" in text


def test_auto_mode_is_effective(capsys, monkeypatch):
    """RF-2b dejo de aplicar (T5): auto esta implementado."""
    import src.main as main_mod

    monkeypatch.setattr(config, "apply_mode", "auto")
    mode = main_mod.effective_apply_mode()
    out = capsys.readouterr().out
    assert mode == "auto"
    assert "no implementado" not in out


def test_run_auto_executes_batch(tmp_path, monkeypatch):
    """RF-3/RF-4: auto envia los matches filtrados con limite y registro."""
    from pathlib import Path

    from apply_helpers import FakePage

    import src.main as main_mod
    from src.apply.ledger import ApplicationLedger
    from src.apply.maintenance import FamilyStatus

    monkeypatch.setattr(config, "apply_mode", "auto")
    monkeypatch.setattr(config, "apply_paused", False)
    monkeypatch.setattr(config, "apply_daily_limit", 5)
    form = (Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "ats_greenhouse_min.html").read_text(
        encoding="utf-8"
    )
    job = _job()
    job.apply_url = "https://job-boards.greenhouse.io/acme/jobs/1"
    report = main_mod.run_auto(
        [job],
        profile={
            "name": "José E. Jiménez",
            "email": "jose@example.com",
            "location": "Caracas, Venezuela",
            "phone": "+58 412 000 0000",
        },
        page_factory=lambda j: FakePage(form),
        ledger=ApplicationLedger(tmp_path / "applications.json"),
        status=FamilyStatus(tmp_path / "family_status.json"),
    )
    assert report is not None
    assert report.sent == 1
    assert report.stopped_reason is None
    entries = ApplicationLedger(tmp_path / "applications.json").load()
    assert entries[0]["outcome"] == "enviado"


def test_run_auto_falls_back_without_browser(capsys, monkeypatch):
    """Si Playwright/navegador no esta disponible, la ejecucion sigue en
    assist (Decision 2 del plan) y no se envia nada."""
    import src.main as main_mod

    def boom():
        raise RuntimeError("sin navegador")

    monkeypatch.setattr(main_mod, "_open_browser", boom)
    report = main_mod.run_auto([], profile={})
    out = capsys.readouterr().out
    assert report is None
    assert "opera en assist" in out


def test_main_sends_only_filtered_matches(monkeypatch):
    """RF-10: en auto solo llegan al runner las ofertas que pasaron
    los filtros de las specs 001 y 002."""
    from datetime import datetime, timedelta, timezone

    import src.main as main_mod

    def make(title, url):
        return JobPost(
            title=title,
            company="Acme",
            location="Remote",
            description="Playwright and Cypress automation for web apps",
            url=url,
            source="Test",
            is_remote=True,
            posted_date=datetime.now(timezone.utc) - timedelta(days=1),
        )

    senior = make("Senior Software Engineer", "https://example.com/job/senior")
    good = make("QA Automation Engineer", "https://example.com/job/good")

    class FakeDB:
        def is_connected(self):
            return False

        def close(self):
            return None

    captured = {}

    class FakeReport:
        processed = 0
        sent = 0
        stopped_reason = None

    def fake_run_auto(jobs, profile=None, **kwargs):
        captured["jobs"] = list(jobs)
        return FakeReport()

    monkeypatch.setattr(config, "apply_mode", "auto")
    monkeypatch.setattr(config, "email_from", "")
    monkeypatch.setattr(config, "openai_api_key", "")
    monkeypatch.setattr(main_mod, "get_scrapers", list)
    monkeypatch.setattr(main_mod, "scrape_all", lambda scrapers, kws: [senior, good])
    monkeypatch.setattr(main_mod, "JobDatabase", lambda *a, **k: FakeDB())
    monkeypatch.setattr(main_mod, "run_auto", fake_run_auto)

    main_mod.main()

    urls = [j.url for j in captured["jobs"]]
    assert good.url in urls
    assert senior.url not in urls
