from pathlib import Path

import requests

from src.config import config
from src.scrapers.linkedin import LinkedInScraper

FIX = Path(__file__).parent / "fixtures"


def test_search_params_window_and_time_date(monkeypatch):
    """RF-8 (spec 001): f_TPR coherente con MAX_DAYS_OLD, sin f_E (lo ignora
    el guest API) y posted_date desde <time datetime>."""
    html = (FIX / "linkedin_guest.html").read_text(encoding="utf-8")
    calls = []

    class FakeResp:
        status_code = 200
        text = html

    def fake_get(url, params=None, **kwargs):
        calls.append(dict(params or {}))
        return FakeResp()

    monkeypatch.setattr(requests, "get", fake_get)

    scraper = LinkedInScraper()
    scraper.max_requests = 1
    jobs = scraper._search()

    assert len(jobs) == 2
    assert len(calls) == 1

    params = calls[0]
    assert params.get("f_E") is None
    assert params.get("f_TPR") == f"r{config.max_days_old * 86400}"
    assert params.get("f_WT") == "2"
    assert params.get("start") == 0
    assert params.get("keywords")
    assert params.get("location")

    assert jobs[0].posted_date is not None
    assert jobs[0].posted_date.day == 3
