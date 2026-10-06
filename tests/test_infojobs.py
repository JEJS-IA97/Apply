from pathlib import Path

from src.scrapers.infojobs import InfoJobsScraper

FIX = Path(__file__).parent / "fixtures"


class FakeResp:
    status_code = 200

    def __init__(self, text):
        self.text = text


def test_infojobs_parses_cards(monkeypatch):
    """RF-13 (spec 002): listado server-rendered de InfoJobs -> JobPost."""
    html = (FIX / "infojobs_list.html").read_text(encoding="utf-8")
    scraper = InfoJobsScraper()
    monkeypatch.setattr(scraper, "request", lambda *a, **k: FakeResp(html))

    jobs = scraper.scrape([])

    assert len(jobs) == 2
    remote = jobs[0]
    assert remote.title == "QA Automation Engineer Remoto"
    assert remote.company == "Acme Testing"
    assert remote.location == "Madrid"
    assert remote.is_remote is True
    assert remote.posted_date is not None
    assert "Cypress" in remote.description
    assert remote.url == (
        "https://www.infojobs.net/madrid/qa-automation-engineer-remoto/"
        "of-i108bdaa3b64facba9d7c1e73941d66"
    )

    presencial = jobs[1]
    assert presencial.is_remote is False
    assert presencial.company == "Testing Sur"
    assert presencial.posted_date is not None
