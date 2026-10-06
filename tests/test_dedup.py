from src.main import dedup_jobs
from src.scrapers.base import JobPost


def _job(url, title="QA Automation Engineer", company="Acme", source="Test"):
    return JobPost(
        title=title, company=company, location="Remote",
        description="Playwright", url=url, source=source,
    )


def test_canonical_url_dedup_first_level():
    """RF-8 (spec 002): mismo anuncio con URLs tracking = una sola vez."""
    a = _job("https://www.linkedin.com/jobs/view/4474345787?trk=feed&utm_source=share")
    b = _job("https://www.linkedin.com/jobs/view/4474345787", source="OtraFuente")
    c = _job("https://www.linkedin.com/jobs/view/4474345787#apply", source="Tercera")
    out = dedup_jobs([a, b, c])
    assert len(out) == 1
    assert out[0].source == "Test"


def test_title_company_dedup_second_level():
    a = _job("https://example.com/job/1", title="QA Automation Engineer", company="Acme")
    b = _job("https://other.com/job/2", title="qa automation engineer", company="ACME")
    out = dedup_jobs([a, b])
    assert len(out) == 1


def test_different_jobs_kept():
    a = _job("https://example.com/job/1")
    b = _job("https://example.com/job/2", title="Frontend Developer")
    out = dedup_jobs([a, b])
    assert len(out) == 2
