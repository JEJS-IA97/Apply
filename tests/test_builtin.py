from pathlib import Path

from src.scrapers.builtin import BuiltInScraper

FIX = Path(__file__).parent / "fixtures"


class FakeResp:
    status_code = 200

    def __init__(self, text):
        self.text = text


def test_builtin_parses_json_ld(monkeypatch):
    """RF-13 (spec 002): ItemList JSON-LD del listado -> JobPost."""
    html = (FIX / "builtin_list.html").read_text(encoding="utf-8")
    scraper = BuiltInScraper()
    monkeypatch.setattr(scraper, "request", lambda *a, **k: FakeResp(html))

    jobs = scraper.scrape([])

    assert len(jobs) == 2
    first = jobs[0]
    assert first.title == "QA Automation Engineer - LATAM (Remote)"
    assert first.url == "https://builtin.com/job/qa-automation-engineer-latam-remote/11480375"
    assert first.is_remote is True
    assert "Playwright" in first.description
    assert jobs[1].title == "Senior Frontend Engineer"
    assert jobs[1].source == "BuiltIn"
