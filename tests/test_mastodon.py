import json
from pathlib import Path

from src.scrapers.mastodon import MastodonScraper

FIX = Path(__file__).parent / "fixtures"


class FakeResp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_mastodon_parses_hiring_status(monkeypatch):
    """RF-4 (spec 002): timeline de hashtag por instancia -> JobPost."""
    payload = json.loads((FIX / "mastodon_tag.json").read_text(encoding="utf-8"))
    scraper = MastodonScraper(instances=["mastodon.social"], hashtags=["#hiring"])
    monkeypatch.setattr(scraper, "request", lambda *a, **k: FakeResp(payload))

    jobs = scraper.scrape([])

    assert len(jobs) == 1
    job = jobs[0]
    assert "QA Automation" in job.title
    assert job.post_source is True
    assert job.is_remote is True
    assert job.posted_date is not None
    assert job.url == "https://mastodon.social/@acme/111"
    assert "Playwright" in job.description
