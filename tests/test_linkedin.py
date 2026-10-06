from pathlib import Path

import requests
from bs4 import BeautifulSoup

from src.scrapers.base import JobPost
from src.scrapers.linkedin import LinkedInScraper, extract_job_id

FIX = Path(__file__).parent / "fixtures"


def test_extract_job_id_from_urn_and_slug():
    """RF-14 (spec 002): id desde urn:li:jobPosting, URL slug y numerica."""
    assert extract_job_id("urn:li:jobPosting:4474345787") == "4474345787"
    assert extract_job_id(
        "https://www.linkedin.com/jobs/view/"
        "qa-automation-engineer-at-acme-corp-4474345787?position=1"
    ) == "4474345787"
    assert extract_job_id("https://www.linkedin.com/jobs/view/1234567890") == "1234567890"
    assert extract_job_id("https://example.com/other") is None
    assert extract_job_id("") is None


def test_parse_cards_with_urn_ids_and_date():
    html = (FIX / "linkedin_guest.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    scraper = LinkedInScraper()
    seen = set()
    jobs = [j for j in (scraper._parse_card(li, seen) for li in soup.select("li")) if j]

    assert len(jobs) == 2
    first = jobs[0]
    assert first.url == "https://www.linkedin.com/jobs/view/4474345787"
    assert first.company == "Acme Corp"
    assert first.location == "Bogotá, Colombia"
    assert first.posted_date is not None
    assert first.posted_date.day == 3
    assert jobs[1].url == "https://www.linkedin.com/jobs/view/4474345788"
    assert jobs[1].is_remote is True


def test_description_enriched_from_job_page(monkeypatch):
    """RF-12 (spec 001): la descripción llega con la petición de detalle."""
    detail = (FIX / "linkedin_job_detail.html").read_text(encoding="utf-8")

    class FakeResp:
        status_code = 200
        text = detail

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResp())

    scraper = LinkedInScraper()
    job = JobPost(
        title="QA Automation Engineer", company="Acme", location="Remote",
        description="", url="https://www.linkedin.com/jobs/view/4474345787",
        source="LinkedIn",
    )
    assert scraper.enrich(job) is True
    assert "Playwright" in job.description
    assert "3+ years" in job.description


def test_enrich_detects_removed_offer(monkeypatch):
    class FakeResp:
        status_code = 404
        text = ""

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResp())

    scraper = LinkedInScraper()
    job = JobPost(
        title="QA Automation Engineer", company="Acme", location="Remote",
        description="", url="https://www.linkedin.com/jobs/view/4474345787",
        source="LinkedIn",
    )
    assert scraper.enrich(job) is False
