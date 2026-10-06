from pathlib import Path

from src.scrapers.web3career import Web3CareerScraper

FIX = Path(__file__).parent / "fixtures"


class FakeResp:
    status_code = 200

    def __init__(self, text):
        self.text = text


def test_web3career_parses_rows(monkeypatch):
    """RF-13 (spec 002): filas tr[data-jobid] de web3.career -> JobPost."""
    html = (FIX / "web3career_list.html").read_text(encoding="utf-8")
    scraper = Web3CareerScraper(search_url="https://web3.career/remote-jobs")
    monkeypatch.setattr(scraper, "request", lambda *a, **k: FakeResp(html))

    jobs = scraper.scrape([])

    assert len(jobs) == 2
    first = jobs[0]
    assert first.title == "QA Automation Engineer"
    assert first.company == "Blockchain Labs"
    assert first.location == "Remote"
    assert first.is_remote is True
    assert first.url == "https://web3.career/qa-automation-engineer-remote/880011"

    second = jobs[1]
    assert second.url == "https://web3.career/senior-solidity-engineer/880012"
    assert second.is_remote is False
