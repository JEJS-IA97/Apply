"""RF-14 y RF-15 (spec 004)."""
from datetime import UTC, datetime, timedelta

from src.analyzer.freshness import check_page, verify_freshness
from src.scrapers.base import JobPost
from src.scrapers.telegram import message_to_job, parse_chats

NOW = datetime(2026, 11, 4, tzinfo=UTC)


def test_parse_chats():
    assert parse_chats("-1004380156934, @vacantes t.me/remotos") == [-1004380156934, "vacantes", "remotos"]


def test_message_to_job_vacante_y_ruido():
    text = "🚀 Vacante: Asistente Virtual\nModalidad 100% remoto\nEnvía tu CV a rrhh@acme.com"
    job = message_to_job(text, NOW, "Empleos LATAM", "https://t.me/c/1/2")
    assert job and job.title.startswith("Vacante: Asistente Virtual") and job.is_remote
    assert job.apply_email == "rrhh@acme.com" and job.post_source and job.url == "https://t.me/c/1/2"
    assert message_to_job("Hola grupo, buenos días a todos 👋 que tengan un lindo día", NOW, "x", "l") is None


def _post(url, desc="Buscamos QA remoto", posted=None):
    return JobPost(title="QA", company="x", location="Remote", description=desc, url=url, source="Telegram",
                   posted_date=posted, is_remote=True, post_source=True)


def test_check_page_cerrada_vencida_vieja():
    assert check_page("<p>No longer accepting applications</p>", 200, NOW, 14)[0] == "oferta_cerrada"
    assert check_page("", 404, NOW, 14)[0] == "oferta_cerrada"
    ld = '<script type="application/ld+json">{"@type":"JobPosting","datePosted":"2026-11-01","validThrough":"2026-10-30"}</script>'
    assert check_page(ld, 200, NOW, 14)[0] == "oferta_cerrada"
    old = '<script type="application/ld+json">{"@type":"JobPosting","datePosted":"2026-09-01"}</script>'
    assert check_page(old, 200, NOW, 14)[0] == "publicacion_vieja"
    ok = '<script type="application/ld+json">{"@type":"JobPosting","datePosted":"2026-11-02"}</script>'
    assert check_page(ok, 200, NOW, 14)[0] == ""


class _Resp:
    def __init__(self, status, text):
        self.status_code, self.text = status, text


class _Session:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url, **kw):
        return self.pages[url]


def test_verify_freshness():
    jobs = [
        _post("https://a.com/1"),
        _post("https://a.com/2"),
        _post("https://t.me/c/1/2", desc="Convocatoria cerrada, gracias"),
        _post("https://a.com/3", posted=NOW - timedelta(days=30)),
    ]
    session = _Session({"https://a.com/1": _Resp(200, "<p>Apply now</p>"),
                        "https://a.com/2": _Resp(200, "<p>This position has been filled</p>")})
    kept, excluded = verify_freshness(jobs, 14, session=session, now=NOW)
    assert [j.url for j in kept] == ["https://a.com/1"]
    assert sorted(r for _, r in excluded) == ["oferta_cerrada", "oferta_cerrada", "publicacion_vieja"]
