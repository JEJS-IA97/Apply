from collections import Counter
from datetime import datetime, timezone

from src.analyzer.cover_letter import CoverLetterGenerator
from src.analyzer.matcher import JobMatcher
from src.apply.batch import BatchReport, run_batch
from src.apply.ledger import ApplicationLedger
from src.apply.maintenance import FamilyStatus
from src.config import apply_mode_from, config
from src.notifier.email_sender import EmailNotifier
from src.profile import load_cv
from src.scrapers.base import JobPost, normalize_url
from src.scrapers.registry import get_scrapers, list_sources
from src.storage.database import JobDatabase


def print_source_status() -> None:
    """RF-1, RF-6 y RF-13 (spec 002): cada fuente no habilitada queda en el
    log con su causa; nada se consulta sin quedar registrado."""
    for spec in list_sources():
        if spec.status == "enabled":
            continue
        print(f"  [{spec.name}] {spec.status.upper()}: {spec.reason}")


def scrape_all(scrapers, keywords: list[str]) -> list[JobPost]:
    all_jobs: list[JobPost] = []
    for scraper in scrapers:
        try:
            print(f"  [{scraper.name}] scraping...")
            jobs = scraper.scrape(keywords)
            if scraper.disabled_reason:
                print(f"    causa: {scraper.disabled_reason}")
            active_jobs = []
            enriched = 0
            for job in jobs:
                if job.posted_date and not scraper.is_recent(job, config.max_days_old):
                    continue
                alive = scraper.enrich(job)
                if alive is False:
                    print(f"    [{scraper.name}] oferta retirada: {job.title[:60]}")
                    continue
                if alive is not None:
                    enriched += 1
                if not scraper.trusts_freshness and not scraper.verify_job_active(job.url):
                    print(f"    [{scraper.name}] verificación fallida: {job.title[:60]}")
                    continue
                active_jobs.append(job)
            extra = f", {enriched} enriquecidas" if enriched else ""
            print(f"  [{scraper.name}] {len(active_jobs)} activas (de {len(jobs)} en bruto{extra})")
            all_jobs.extend(active_jobs)
        except Exception as e:  # noqa: BLE001
            print(f"  [{scraper.name}] ERROR (fuente omitida): {e}")
    return all_jobs


def dedup_jobs(jobs: list[JobPost]) -> list[JobPost]:
    """RF-8 (spec 002): nivel 1 URL canónica; nivel 2 título+empresa."""
    result: list[JobPost] = []
    seen_urls = set()
    seen_titles = set()
    for job in jobs:
        key_url = normalize_url(job.url)
        if key_url and key_url in seen_urls:
            job.excluded_reason = "duplicado_url"
            continue
        key_title = f"{job.title.lower().strip()}|{job.company.lower().strip()}"
        if key_title in seen_titles:
            job.excluded_reason = "duplicado_titulo"
            continue
        if key_url:
            seen_urls.add(key_url)
        seen_titles.add(key_title)
        result.append(job)
    return result


def log_excluded(matcher: JobMatcher) -> None:
    """RF-6 (spec 001): los descartes quedan en el log con su causa."""
    counts = Counter(reason for _, _, reason in matcher.last_excluded)
    if not counts:
        return
    print("\nDescartados por filtro:")
    for reason, total in counts.most_common():
        print(f"  {reason}: {total}")


def effective_apply_mode() -> str:
    """RF-2b dejó de aplicar (T5): `auto` está implementado y opera con
    límite diario, pausa y registro. El fallback a `assist` solo ocurre
    si el navegador no está disponible (Decisión 2 del plan)."""
    return apply_mode_from(config.apply_mode)


def _open_browser():
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.launch(headless=True)
    except Exception:
        playwright.stop()
        raise
    return playwright, browser


def run_auto(
    jobs: list[JobPost],
    profile: dict | None = None,
    *,
    page_factory=None,
    ledger: ApplicationLedger | None = None,
    status: FamilyStatus | None = None,
) -> BatchReport | None:
    """RF-3/RF-4/RF-8/RF-9: envía los matches filtrados (RF-10) con el
    límite y la pausa de configuración. Devuelve None si el navegador
    no está disponible (la ejecución sigue en assist)."""
    if profile is None:
        profile = load_cv()
    if ledger is None:
        ledger = ApplicationLedger()
    if status is None:
        status = FamilyStatus()
    if page_factory is None:
        try:
            playwright, browser = _open_browser()
        except Exception as exc:  # noqa: BLE001
            print(f"  [auto] navegador no disponible ({type(exc).__name__}: {exc}) -> opera en assist")
            return None
        try:
            return run_batch(
                jobs,
                profile,
                ledger=ledger,
                page_factory=lambda job: browser.new_page(),
                daily_limit=config.apply_daily_limit,
                paused=config.apply_paused,
                status=status,
            )
        finally:
            browser.close()
            playwright.stop()
    return run_batch(
        jobs,
        profile,
        ledger=ledger,
        page_factory=page_factory,
        daily_limit=config.apply_daily_limit,
        paused=config.apply_paused,
        status=status,
    )


def main():
    mode = effective_apply_mode()
    print("=" * 60)
    print(f"Job Scraper Bot - {datetime.now(timezone.utc).isoformat()}")
    print(f"Modo de postulacion: {mode}")
    print("=" * 60)

    db = JobDatabase(config.mongo_uri, config.mongo_db)
    if not db.is_connected():
        print("WARNING: MongoDB not available, running without persistence")

    print("\nEstado de fuentes:")
    print_source_status()

    scrapers = get_scrapers()
    print(f"\nScraping {len(scrapers)} platforms habilitadas...")
    all_jobs = scrape_all(scrapers, config.search_keywords)
    print(f"\nTotal raw: {len(all_jobs)}")

    deduped = dedup_jobs(all_jobs)
    print(f"Tras dedup (URL canonica + titulo+empresa): {len(deduped)}")

    matcher = JobMatcher()
    filtered = matcher.filter_jobs(deduped)
    print(f"Tras filtros CV (score>={matcher.min_score}): {len(filtered)}")
    log_excluded(matcher)

    if not filtered:
        print("No matching jobs found")
        if db.is_connected():
            db.close()
        return

    new_jobs = []
    for job in filtered:
        if db.is_connected() and db.is_duplicate(job.url):
            continue
        new_jobs.append(job)

    print(f"Nuevas (no enviadas antes): {len(new_jobs)}")

    if not new_jobs:
        print("All jobs already sent previously")
        if db.is_connected():
            db.close()
        return

    cover_gen = CoverLetterGenerator(openai_api_key=config.openai_api_key)
    for job in new_jobs:
        job.cover_letter = cover_gen.generate(job)
        if db.is_connected():
            db.save_job({
                "title": job.title, "company": job.company,
                "location": job.location, "description": job.description,
                "url": job.url, "source": job.source,
                "posted_date": job.posted_date.isoformat() if job.posted_date else None,
                "match_score": job.match_score, "cover_letter": job.cover_letter,
                "apply_url": job.apply_url
            })

    print(f"\n--- TOP {len(new_jobs)} MATCHES ---")
    for j in new_jobs[:15]:
        print(f"  [{j.match_score}%] {j.title} @ {j.company} ({j.source}) | {j.location}")

    if mode == "auto":
        auto_report = run_auto(new_jobs)
        if auto_report is None:
            config.apply_mode = "assist"
            mode = "assist"
        else:
            print(f"\nMODO AUTO: {auto_report.processed} procesadas, {auto_report.sent} enviadas")
            if auto_report.stopped_reason:
                print(f"  parada: {auto_report.stopped_reason}")

    if mode == "assist":
        print("\nMODO ASISTIDO: no se envia ninguna postulacion automatica.")
        print("El reporte incluye la carta y la checklist de revision manual por oferta.")

    if config.email_from and config.email_password:
        notifier = EmailNotifier(
            from_addr=config.email_from,
            password=config.email_password,
            to_addr=config.email_to
        )
        sent = notifier.send_jobs_report(new_jobs)
        print(f"\nEmail {'sent' if sent else 'FAILED'}")
        if db.is_connected():
            db.mark_all_sent()

    if db.is_connected():
        db.close()

    print("Done!")


if __name__ == "__main__":
    main()
