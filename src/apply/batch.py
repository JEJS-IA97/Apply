"""Fase 2, T3-T4 (spec 003): lote de postulaciones con límite, pausa y
parada ante bloqueos.

RF-4: límite de envíos por ejecución y por día (el contador diario
viene del registro persistente). RF-8: cada intento de la ruta de
envío queda registrado antes de continuar. RF-9: con la pausa activada
no se intenta nada en la ejecución. RF-7: un CAPTCHA interactivo detiene
el lote entero; un control de acceso detiene el lote si aparece en la
primera oferta (caso límite de la spec).
"""

from dataclasses import dataclass, field
from datetime import datetime

from src.apply.ledger import ApplicationLedger, entry_for, save_evidence
from src.apply.maintenance import FamilyStatus
from src.apply.runner import ApplyResult, resolve_ats_url, run_application
from src.scrapers.base import JobPost

RECORDED_OUTCOMES = ("enviado", "dato_faltante", "error", "bloqueo")


@dataclass
class BatchReport:
    processed: int = 0
    sent: int = 0
    stopped_reason: str | None = None
    results: list[tuple[JobPost, ApplyResult]] = field(default_factory=list)


def run_batch(
    jobs: list[JobPost],
    profile: dict,
    *,
    ledger: ApplicationLedger,
    page_factory,
    daily_limit: int,
    paused: bool = False,
    resolver=resolve_ats_url,
    now: datetime | None = None,
    status: FamilyStatus | None = None,
) -> BatchReport:
    report = BatchReport()
    if paused:
        report.stopped_reason = "pausado"
        return report
    if status is None:
        status = FamilyStatus()
    sent_this_run = 0
    for job in jobs:
        if sent_this_run >= daily_limit or ledger.sent_today(now) >= daily_limit:
            report.stopped_reason = "limite_diario"
            break
        raw_url = (job.apply_url or "").strip()
        ats_url = resolver(raw_url) if raw_url else None
        page = page_factory(job)
        result = run_application(
            job,
            profile,
            page,
            resolver=resolver,
            ats_url=ats_url,
            status=status,
        )
        if result.outcome in RECORDED_OUTCOMES:
            entry = entry_for(job, ats_url or raw_url, result)
            if result.outcome == "enviado":
                evidence_path = save_evidence(result, ledger.path.parent / "evidence")
                if evidence_path:
                    entry["evidence_path"] = evidence_path
            ledger.record(entry)
        report.results.append((job, result))
        if result.outcome == "enviado":
            sent_this_run += 1
            report.sent += 1
        elif result.outcome == "bloqueo":
            if result.detail == "captcha":
                report.stopped_reason = "captcha_detectado"
                break
            if result.detail == "login" and len(report.results) == 1:
                report.stopped_reason = "login_primera_oferta"
                break
    report.processed = len(report.results)
    return report
