from datetime import datetime, timedelta, timezone

import requests

from src.scrapers.base import BaseScraper, JobPost, normalize_url


class DummyScraper(BaseScraper):
    def __init__(self, name="Dummy", jobs=None, verify_result=True, trusted=False):
        super().__init__(name)
        self._jobs = jobs or []
        self.verify_result = verify_result
        self.verify_calls = 0
        self.trusts_freshness = trusted

    def scrape(self, keywords):
        return list(self._jobs)

    def verify_job_active(self, url):
        self.verify_calls += 1
        return self.verify_result


def _recent_job():
    return JobPost(
        title="QA Automation Engineer",
        company="Acme",
        location="Remote",
        description="Playwright",
        url="https://example.com/job/1",
        source="Dummy",
        posted_date=datetime.now(timezone.utc) - timedelta(days=1),
    )


def test_request_budget_per_source(monkeypatch):
    """RF-9 (spec 002): cada fuente se detiene en su presupuesto."""
    calls = {"n": 0}

    class FakeResp:
        status_code = 200

    def fake_get(url, **kwargs):
        calls["n"] += 1
        return FakeResp()

    monkeypatch.setattr(requests, "get", fake_get)

    scraper = DummyScraper()
    scraper.max_requests = 2
    assert scraper.request("https://example.com/a") is not None
    assert scraper.request("https://example.com/b") is not None
    assert scraper.request("https://example.com/c") is None
    assert scraper.requests_made == 2
    assert calls["n"] == 2


def test_normalize_url_strips_tracking():
    """RF-8 (spec 002): URL canonica sin utm/trk/ref ni fragmentos."""
    a = "https://www.linkedin.com/jobs/view/4474345787?trk=x&utm_source=feed&refId=abc#comment"
    b = "https://WWW.linkedin.com/jobs/view/4474345787/"
    assert normalize_url(a) == normalize_url(b)
    assert normalize_url(a) == "https://www.linkedin.com/jobs/view/4474345787"
    assert normalize_url("") == ""


def test_post_source_bypasses_keyword_gate():
    """Decision 6 (spec 002): los posts no se prefiltran por keywords;
    el gate de relevancia del matcher (RF-13) decide."""
    scraper = DummyScraper()
    feed = JobPost(
        title="Company Is Hiring",
        company="Acme",
        location="Remote",
        description="Company Is Hiring",
        url="https://example.com/job/2",
        source="Dummy",
    )
    post = JobPost(
        title="Company Is Hiring",
        company="Acme",
        location="Remote",
        description="Company Is Hiring",
        url="https://example.com/job/3",
        source="Dummy",
        post_source=True,
    )
    out = scraper.filter_keyword_jobs([feed, post], ["QA Automation"])
    assert out == [post]
    assert feed.excluded_reason is None


def test_trusted_feed_skips_verify(monkeypatch):
    """RF-15 (spec 002): feeds de confianza no hacen verify por oferta."""
    from src.main import scrape_all

    trusted = DummyScraper("Trusted", jobs=[_recent_job()], trusted=True)

    def boom(url):
        raise AssertionError("verify_job_active no debe llamarse en feeds de confianza")

    trusted.verify_job_active = boom

    out = scrape_all([trusted], [])
    assert len(out) == 1


def test_untrusted_source_verifies_each_job():
    from src.main import scrape_all

    ok = DummyScraper("Untrusted", jobs=[_recent_job()], verify_result=True, trusted=False)
    out = scrape_all([ok], [])
    assert len(out) == 1
    assert ok.verify_calls == 1

    dead = DummyScraper("Dead", jobs=[_recent_job()], verify_result=False, trusted=False)
    out = scrape_all([dead], [])
    assert out == []
    assert dead.verify_calls == 1
