import json
from pathlib import Path

import requests

from src.scrapers.getonboard import GetOnBoardScraper
from src.scrapers.linkedin import LinkedInScraper
from src.scrapers.torre import TorreScraper

FIX = Path(__file__).parent / "fixtures"


def test_torre_parse_opportunity():
    """RF-7 (spec 004): Torre se mapea con idioma, sueldo y ubicación."""
    data = json.loads((FIX / "torre_opportunity.json").read_text(encoding="utf-8"))
    job = TorreScraper.parse_opportunity(data, "devups-qa-uxui-qa-uxui-specialist")
    assert job.title.startswith("QA UX/UI")
    assert job.company == "DevUps"
    assert job.location == "Remote (Worldwide)"
    assert "English: conversational" in job.description
    assert job.salary.startswith("1500-2000 USD")
    assert job.url == "https://torre.ai/post/kWRgM0ew-devups-qa-uxui-qa-uxui-specialist"


def test_torre_closed_opportunity_skipped():
    data = json.loads((FIX / "torre_opportunity.json").read_text(encoding="utf-8"))
    data["status"] = "closed"
    assert TorreScraper.parse_opportunity(data, "x") is None


def test_getonboard_keeps_only_fully_remote_up_to_semisenior():
    """RF-7 (spec 004): fuera senior y remoto-local."""
    data = json.loads((FIX / "getonboard_search.json").read_text(encoding="utf-8"))
    jobs = [j for j in (GetOnBoardScraper.parse_item(i) for i in data["data"]) if j]
    assert [j.title for j in jobs] == ["QA Analyst"]
    assert jobs[0].company == "Zaelot"
    assert jobs[0].location == "Remote (Worldwide)"
    assert "Postman" in jobs[0].description


def test_linkedin_waits_between_requests(monkeypatch):
    """RF-6 (spec 004): pausa entre peticiones a LinkedIn."""
    sleeps = []

    class FakeResp:
        status_code = 200
        text = ""

    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResp())
    monkeypatch.setattr("src.scrapers.linkedin.time.sleep", lambda s: sleeps.append(s))
    scraper = LinkedInScraper()
    scraper.max_requests = 3
    scraper._search()
    assert sleeps == [scraper.request_delay, scraper.request_delay]


def test_env_aliases(monkeypatch):
    """RF-8 (spec 004): nombres alternativos del .env."""
    from src.config import env
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    assert env("EMAIL_FROM", "", "SMTP_USER") == "bot@example.com"
    monkeypatch.setenv("EMAIL_FROM", "main@example.com")
    assert env("EMAIL_FROM", "", "SMTP_USER") == "main@example.com"
