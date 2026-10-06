from src.config import config
from src.scrapers.registry import REMOTEOK_REASON, get_scrapers, list_sources


def _specs():
    return {s.name: s for s in list_sources()}


def test_blocked_source_never_built():
    """RF-12 (spec 002): RemoteOK bloqueada, con causa, sin constructor."""
    spec = _specs()["remoteok"]
    assert spec.status == "disabled"
    assert spec.reason == REMOTEOK_REASON
    assert spec.builder is None
    assert not any("remoteok" in s.name.lower() for s in get_scrapers())


def test_every_non_enabled_source_has_reason():
    """RF-13 (spec 002): cada fuente no habilitada queda con su causa."""
    for spec in list_sources():
        if spec.status != "enabled":
            assert spec.reason.strip(), f"{spec.name} sin causa"
        else:
            assert spec.builder is not None, f"{spec.name} habilitada sin constructor"


def test_unreachable_sources_disabled_with_reason():
    """RF-10/RF-13 (spec 002): fuentes inaccesibles registradas con causa."""
    specs = _specs()
    for name in ("getonboard", "indeed", "bluesky", "tecnoempleo", "dice", "flexjobs"):
        spec = specs[name]
        assert spec.status in ("disabled", "pending"), f"{name}: {spec.status}"
        assert spec.reason.strip()


def test_linkedin_posts_gated(monkeypatch):
    """RF-11 (spec 002): LinkedIn posts requiere credenciales + Playwright."""
    monkeypatch.setattr(config, "linkedin_email", "")
    monkeypatch.setattr(config, "linkedin_password", "")
    spec = _specs()["linkedin_posts"]
    assert spec.status == "disabled"
    assert "LINKEDIN" in spec.reason
    assert spec.builder is None


def test_enabled_sources_build_without_network():
    specs = _specs()
    enabled = [name for name, s in specs.items() if s.status == "enabled"]
    for name in ("remotive", "weworkremotely", "hackernews", "mastodon",
                 "web3career", "infojobs", "builtin", "linkedin"):
        assert name in enabled

    scrapers = get_scrapers()
    names = {s.name for s in scrapers}
    assert "HackerNews" in names
    assert "Mastodon" in names
    assert "InfoJobs" in names
    assert "BuiltIn" in names
    for scraper in scrapers:
        assert scraper.max_requests > 0
