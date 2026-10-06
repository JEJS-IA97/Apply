import json
from pathlib import Path

from src.scrapers.hn import HackerNewsScraper

FIX = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_hn_job_board_parses(monkeypatch):
    """RF-2 (spec 002): tablero tags=job con fecha y empresa."""
    scraper = HackerNewsScraper()
    board = _load("hn_job_board.json")["hits"]
    story = _load("hn_hiring_story.json")["hits"]
    comments = _load("hn_comments.json")["hits"]

    def fake_get(params):
        if params.get("tags") == "job":
            return board
        if params.get("tags") == "story":
            return story
        if params.get("tags") == "comment":
            return comments
        return []

    monkeypatch.setattr(scraper, "_get", fake_get)
    jobs = scraper.scrape([])

    board_jobs = [j for j in jobs if j.url == "https://example.com/careers"]
    assert len(board_jobs) == 1
    first = board_jobs[0]
    assert first.company == "Example Corp"
    assert first.posted_date is not None
    assert first.posted_date.year == 2026
    assert first.post_source is True
    assert first.is_remote is True

    hiring_story = [j for j in jobs if "42000002" in (j.url or "")]
    if hiring_story:
        assert hiring_story[0].company == ""


def test_hn_hiring_thread_comments(monkeypatch):
    """RF-2 (spec 002): comentarios del hilo con formato Company | Role | Location."""
    scraper = HackerNewsScraper()
    story = _load("hn_hiring_story.json")["hits"]
    comments = _load("hn_comments.json")["hits"]

    def fake_get(params):
        if params.get("tags") == "job":
            return []
        if params.get("tags") == "story":
            return story
        if params.get("tags") == "comment":
            return comments
        return []

    monkeypatch.setattr(scraper, "_get", fake_get)
    jobs = scraper.scrape([])

    pipe_job = next(j for j in jobs if "42100101" in j.url)
    assert pipe_job.company == "AcmeQA"
    assert pipe_job.title.startswith("QA Automation Engineer (Mid)")
    assert pipe_job.location.startswith("Remote (Americas)")
    assert pipe_job.description and "Playwright" in pipe_job.description
    assert pipe_job.posted_date is not None
    assert pipe_job.post_source is True

    assert not any("42100102" in j.url for j in jobs)

    fallback = next(j for j in jobs if "42100103" in j.url)
    assert "Frontend Developer" in fallback.title
    assert fallback.is_remote is True
