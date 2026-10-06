from datetime import datetime, timedelta, timezone

from src.main import scrape_all
from src.scrapers.base import JobPost


class OkScraper:
    name = "OkSource"
    trusts_freshness = True
    requests_made = 0
    max_requests = 5
    disabled_reason = ""

    def __init__(self):
        self.job = JobPost(
            title="QA Automation Engineer",
            company="Acme",
            location="Remote",
            description="Playwright",
            url="https://example.com/job/ok",
            source="OkSource",
            posted_date=datetime.now(timezone.utc) - timedelta(days=1),
        )

    def scrape(self, keywords):
        return [self.job]

    def enrich(self, job):
        return None

    def verify_job_active(self, url):
        return True

    def is_recent(self, job, max_days=7):
        return True


class BoomScraper:
    name = "BoomSource"
    trusts_freshness = False
    requests_made = 0
    max_requests = 5
    disabled_reason = ""

    def scrape(self, keywords):
        raise RuntimeError("fuente caida")

    def verify_job_active(self, url):
        return True


def test_failing_source_does_not_abort_run(capsys):
    """RF-6 (spec 002): una fuente que falla no aborta el resto del run."""
    ok = OkScraper()
    out = scrape_all([BoomScraper(), ok], [])
    assert [j.url for j in out] == ["https://example.com/job/ok"]
    printed = capsys.readouterr().out
    assert "BoomSource" in printed
    assert "ERROR" in printed


def test_remoteok_is_never_consulted(capsys):
    """RF-12 (spec 002): RemoteOK bloqueada no llega al pipeline."""
    from src.scrapers.registry import get_scrapers

    names = [s.name for s in get_scrapers()]
    assert not any("remoteok" in n.lower() for n in names)
