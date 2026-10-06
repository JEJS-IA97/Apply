import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from apply_helpers import FakePage

from src.apply.batch import run_batch
from src.apply.ledger import ApplicationLedger, entry_for
from src.apply.runner import ApplyResult
from src.config import apply_paused_from
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


def _job(n=1, url=GREENHOUSE_URL):
    return JobPost(
        title=f"QA Automation Engineer {n}",
        company="Acme",
        location="Remote",
        description="Playwright",
        url=f"{url}?ref={n}",
        apply_url=url,
        source="Test",
    )


def _entry(outcome="enviado", stamp=None):
    moment = stamp or datetime.now(timezone.utc)
    return {"outcome": outcome, "timestamp": moment.isoformat()}


def test_ledger_records_and_persists(tmp_path):
    """RF-8: oferta, dominio, fecha, resultado y motivo quedan en disco."""
    path = tmp_path / "applications.json"
    ledger = ApplicationLedger(path)
    result = ApplyResult(outcome="enviado", family="greenhouse", confirmation_url=GREENHOUSE_URL + "?ok")
    ledger.record(entry_for(_job(), GREENHOUSE_URL, result))
    entries = ledger.load()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["domain"] == "job-boards.greenhouse.io"
    assert entry["family"] == "greenhouse"
    assert entry["outcome"] == "enviado"
    datetime.fromisoformat(entry["timestamp"])

    reloaded = ApplicationLedger(path).load()
    assert reloaded == entries


def test_sent_today_counts_only_today(tmp_path):
    """RF-4: el contador diario solo cuenta envíos de hoy."""
    ledger = ApplicationLedger(tmp_path / "applications.json")
    now = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    ledger.record(_entry("enviado", now))
    ledger.record(_entry("enviado", now - timedelta(days=1)))
    ledger.record(_entry("dato_faltante", now))
    ledger.record(_entry("error", now))
    assert ledger.sent_today(now) == 1
    assert ledger.sent_today(now + timedelta(days=1)) == 0


def test_batch_respects_execution_limit(tmp_path):
    """RF-4: el lote se detiene al alcanzar el límite."""
    ledger = ApplicationLedger(tmp_path / "applications.json")
    calls = []

    def factory(job):
        calls.append(job)
        return FakePage(MIN_FORM)

    report = run_batch(
        [_job(1), _job(2), _job(3)],
        PROFILE,
        ledger=ledger,
        page_factory=factory,
        daily_limit=2,
        resolver=lambda u: u,
        now=datetime.now(timezone.utc),
    )
    assert report.sent == 2
    assert report.processed == 2
    assert report.stopped_reason == "limite_diario"
    assert len(calls) == 2
    assert len(ledger.load()) == 2


def test_batch_respects_daily_limit_from_previous_run(tmp_path):
    """RF-4: el límite diario persiste entre ejecuciones."""
    ledger = ApplicationLedger(tmp_path / "applications.json")
    today = datetime.now(timezone.utc)
    ledger.record(_entry("enviado", today))
    ledger.record(_entry("enviado", today))
    calls = []

    def factory(job):
        calls.append(job)
        return FakePage(MIN_FORM)

    report = run_batch(
        [_job(1)],
        PROFILE,
        ledger=ledger,
        page_factory=factory,
        daily_limit=2,
        resolver=lambda u: u,
        now=today,
    )
    assert report.stopped_reason == "limite_diario"
    assert report.processed == 0
    assert calls == []


def test_batch_paused_does_nothing(tmp_path):
    """RF-9: con la pausa activa no se intenta nada ni se registra."""
    ledger = ApplicationLedger(tmp_path / "applications.json")
    calls = []
    report = run_batch(
        [_job(1)],
        PROFILE,
        ledger=ledger,
        page_factory=lambda job: calls.append(job),
        daily_limit=5,
        paused=True,
        resolver=lambda u: u,
    )
    assert report.stopped_reason == "pausado"
    assert report.processed == 0
    assert calls == []
    assert ledger.load() == []
    assert not (tmp_path / "applications.json").exists()


def test_unsupported_domain_not_recorded(tmp_path):
    """RF-8: dominio_no_soportado no es un intento de envío."""
    ledger = ApplicationLedger(tmp_path / "applications.json")
    report = run_batch(
        [_job(1, url="https://example.com/careers/1")],
        PROFILE,
        ledger=ledger,
        page_factory=lambda job: FakePage(MIN_FORM),
        daily_limit=5,
        resolver=lambda u: u,
    )
    assert report.results[0][1].outcome == "dominio_no_soportado"
    assert ledger.load() == []


def test_failed_attempt_is_recorded(tmp_path):
    """RF-8: los fallos quedan con su motivo."""
    ledger = ApplicationLedger(tmp_path / "applications.json")
    report = run_batch(
        [_job(1)],
        PROFILE,
        ledger=ledger,
        page_factory=lambda job: FakePage(MIN_FORM, confirm_on_submit=False),
        daily_limit=5,
        resolver=lambda u: u,
    )
    assert report.results[0][1].outcome == "error"
    entries = ledger.load()
    assert len(entries) == 1
    assert entries[0]["outcome"] == "error"
    assert entries[0]["detail"]


def test_ledger_file_is_valid_json(tmp_path):
    path = tmp_path / "applications.json"
    ledger = ApplicationLedger(path)
    result = ApplyResult(outcome="dato_faltante", family="greenhouse", detail="phone")
    ledger.record(entry_for(_job(), GREENHOUSE_URL, result))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, list) and data[0]["detail"] == "phone"


def test_sent_entry_persists_evidence(tmp_path):
    """RF-3: la captura/HTML de confirmación queda en disco y su ruta
    se registra en la entrada del ledger."""
    ledger = ApplicationLedger(tmp_path / "applications.json")
    report = run_batch(
        [_job(1)],
        PROFILE,
        ledger=ledger,
        page_factory=lambda job: FakePage(MIN_FORM),
        daily_limit=5,
        resolver=lambda u: u,
    )
    assert report.sent == 1
    entry = ledger.load()[0]
    assert "evidence_path" in entry
    evidence = Path(entry["evidence_path"])
    assert evidence.exists()
    assert evidence.parent == tmp_path / "evidence"
    assert evidence.read_text(encoding="utf-8") == report.results[0][1].evidence
    assert "confirmation" in evidence.read_text(encoding="utf-8").lower()


def test_failed_attempt_has_no_evidence_file(tmp_path):
    """RF-3: solo los envíos guardan evidencia; un fallo no crea HTML."""
    ledger = ApplicationLedger(tmp_path / "applications.json")
    run_batch(
        [_job(1)],
        PROFILE,
        ledger=ledger,
        page_factory=lambda job: FakePage(MIN_FORM, confirm_on_submit=False),
        daily_limit=5,
        resolver=lambda u: u,
    )
    entry = ledger.load()[0]
    assert entry["outcome"] == "error"
    assert "evidence_path" not in entry
    assert not (tmp_path / "evidence").exists()


def test_apply_paused_parsing():
    """RF-9: flag/env de pausa."""
    assert apply_paused_from("") is False
    assert apply_paused_from("0") is False
    assert apply_paused_from("1") is True
    assert apply_paused_from("TRUE") is True
    assert apply_paused_from("yes") is True
