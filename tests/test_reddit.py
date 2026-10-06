from src.config import config
from src.scrapers.reddit import RedditScraper
from src.scrapers.registry import list_sources


def test_reddit_disabled_without_credentials(monkeypatch):
    """RF-5 (spec 002): sin credenciales queda disabled con causa, no vacio."""
    monkeypatch.setattr(config, "reddit_client_id", "")
    monkeypatch.setattr(config, "reddit_client_secret", "")
    spec = {s.name: s for s in list_sources()}["reddit"]
    assert spec.status == "disabled"
    assert "REDDIT_CLIENT_ID" in spec.reason
    assert "403" in spec.reason
    assert spec.builder is None


def test_reddit_reads_profile_lists():
    scraper = RedditScraper()
    assert "QualityAssurance" in scraper.subreddits
    assert scraper.search_terms
    assert scraper.praw is None
