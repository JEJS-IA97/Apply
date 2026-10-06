from collections.abc import Callable
from dataclasses import dataclass

from src.config import config
from src.scrapers.base import BaseScraper

EVIDENCE = "evidencia 2026-10-06"

REMOTEOK_REASON = (
    "Reportada por el usuario como estafa (ofertas que redirigen a LinkedIn, "
    "cancelación de suscripción impedida, contacto inexistente): bloqueada por RF-12 (spec 002)"
)


@dataclass(frozen=True)
class SourceSpec:
    name: str
    kind: str
    status: str          # "enabled" | "disabled" | "pending"
    reason: str = ""
    builder: Callable[[], BaseScraper] | None = None
    max_requests: int = 30


def _build_remotive() -> BaseScraper:
    from src.scrapers.remotive import RemotiveScraper
    return RemotiveScraper()


def _build_wwr() -> BaseScraper:
    from src.scrapers.weworkremotely import WeWorkRemotelyScraper
    return WeWorkRemotelyScraper()


def _build_arbeitnow() -> BaseScraper:
    from src.scrapers.arbeitnow import ArbeitnowScraper
    return ArbeitnowScraper()


def _build_himalayas() -> BaseScraper:
    from src.scrapers.himalayas import HimalayasScraper
    return HimalayasScraper()


def _build_linkedin() -> BaseScraper:
    from src.scrapers.linkedin import LinkedInScraper
    return LinkedInScraper(email=config.linkedin_email, password=config.linkedin_password)


def _build_hackernews() -> BaseScraper:
    from src.scrapers.hn import HackerNewsScraper
    return HackerNewsScraper()


def _build_mastodon() -> BaseScraper:
    from src.scrapers.mastodon import MastodonScraper
    return MastodonScraper()


def _build_web3career() -> BaseScraper:
    from src.scrapers.web3career import Web3CareerScraper
    return Web3CareerScraper()


def _build_reddit() -> BaseScraper:
    from src.scrapers.reddit import RedditScraper
    return RedditScraper(
        client_id=config.reddit_client_id,
        client_secret=config.reddit_client_secret,
        user_agent=config.reddit_user_agent,
    )


def _build_linkedin_posts() -> BaseScraper:
    from src.scrapers.linkedin_posts import LinkedInPostsScraper
    return LinkedInPostsScraper(email=config.linkedin_email, password=config.linkedin_password)


def _build_infojobs() -> BaseScraper:
    from src.scrapers.infojobs import InfoJobsScraper
    return InfoJobsScraper()


def _build_builtin() -> BaseScraper:
    from src.scrapers.builtin import BuiltInScraper
    return BuiltInScraper()


def _reddit_status() -> tuple:
    if config.reddit_client_id and config.reddit_client_secret:
        return "enabled", ""
    return "disabled", (
        "Faltan REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET en .env "
        f"(el JSON público responde 403, {EVIDENCE})"
    )


def _linkedin_posts_status() -> tuple:
    if not (config.linkedin_email and config.linkedin_password):
        return "disabled", "Faltan LINKEDIN_EMAIL/LINKEDIN_PASSWORD en .env"
    from src.scrapers.linkedin_posts import playwright_available
    if not playwright_available():
        return "disabled", "Falta la dependencia playwright (pip install playwright && playwright install chromium)"
    return "enabled", ""


def list_sources() -> list[SourceSpec]:
    """RF-1, RF-12 y RF-13 (spec 002): inventario único de fuentes aprobadas
    con estado y causa. Las fuentes bloqueadas nunca se construyen."""
    reddit_status, reddit_reason = _reddit_status()
    posts_status, posts_reason = _linkedin_posts_status()

    sources = [
        SourceSpec("remotive", "job_board", "enabled", builder=_build_remotive),
        SourceSpec("weworkremotely", "job_board", "enabled", builder=_build_wwr),
        SourceSpec("arbeitnow", "job_board", "enabled", builder=_build_arbeitnow),
        SourceSpec("himalayas", "job_board", "enabled", builder=_build_himalayas),
        SourceSpec("linkedin", "job_board", "enabled", builder=_build_linkedin, max_requests=40),
        SourceSpec("hackernews", "forum", "enabled", builder=_build_hackernews, max_requests=6),
        SourceSpec("mastodon", "post", "enabled", builder=_build_mastodon, max_requests=30),
        SourceSpec("web3career", "job_board", "enabled", builder=_build_web3career, max_requests=5),
        SourceSpec("infojobs", "job_board", "enabled", builder=_build_infojobs, max_requests=5),
        SourceSpec("builtin", "job_board", "enabled", builder=_build_builtin, max_requests=3),
        SourceSpec("reddit", "forum", reddit_status, reddit_reason,
                   builder=_build_reddit if reddit_status == "enabled" else None, max_requests=15),
        SourceSpec("linkedin_posts", "post", posts_status, posts_reason,
                   builder=_build_linkedin_posts if posts_status == "enabled" else None, max_requests=12),

        SourceSpec("remoteok", "job_board", "disabled", REMOTEOK_REASON),
        SourceSpec("indeed", "job_board", "disabled",
                   f"403 Forbidden desde el entorno ({EVIDENCE}); fuente anti-bot, RF-10 prohíbe eludir controles"),
        SourceSpec("bluesky", "post", "disabled",
                   f"API pública devuelve 403 desde el entorno ({EVIDENCE})"),
        SourceSpec("telegram", "post", "pending",
                   "Requiere TELEGRAM_API_ID/TELEGRAM_API_HASH y la dependencia telethon"),
        SourceSpec("getonboard", "job_board", "pending",
                   f"Listado renderizado por JS y /search devuelve 404 ({EVIDENCE})"),
        SourceSpec("levelsfiy", "job_board", "pending", f"SPA sin API pública ({EVIDENCE})"),
        SourceSpec("arc", "job_board", "pending", f"SPA sin API pública ({EVIDENCE})"),
        SourceSpec("lemonio", "job_board", "pending", f"Sin listado público (solo landing) ({EVIDENCE})"),
        SourceSpec("welcometothejungle", "job_board", "pending",
                   f"Responde 202 con reto anti-bot ({EVIDENCE})"),
        SourceSpec("toptal", "job_board", "pending", f"Sin página de trabajos pública (/jobs -> 404) ({EVIDENCE})"),
        SourceSpec("flexjobs", "job_board", "pending", f"403 y modelo de pago ({EVIDENCE})"),
        SourceSpec("glassdoor", "job_board", "pending",
                   f"Listado con anti-bot/JS; requiere decisión (RF-10) ({EVIDENCE})"),
        SourceSpec("dice", "job_board", "pending", f"403 desde el entorno ({EVIDENCE})"),
        SourceSpec("tecnoempleo", "job_board", "pending", f"403 desde el entorno ({EVIDENCE})"),
        SourceSpec("fiverr", "job_board", "pending",
                   f"403 y es marketplace de freelancing, no bolsa de empleo ({EVIDENCE})"),
        SourceSpec("wellfound", "job_board", "pending", f"Listado JS con anti-bot ({EVIDENCE})"),
        SourceSpec("googlejobs", "job_board", "pending",
                   "Sin API oficial; requiere decisión sobre SerpAPI de pago o scraping de Google (RF-10)"),
        SourceSpec("remotolist", "job_board", "pending",
                   f"Dominio no confirmado (remotelist.com reinicia la conexión, {EVIDENCE})"),
        SourceSpec("talently", "job_board", "pending", f"Dominio no confirmado ({EVIDENCE})"),
    ]
    return sources


def get_scrapers() -> list[BaseScraper]:
    """Construye solo las fuentes habilitadas y disponibles (RF-1)."""
    scrapers: list[BaseScraper] = []
    for spec in list_sources():
        if spec.status != "enabled" or spec.builder is None:
            continue
        try:
            scraper = spec.builder()
            scraper.max_requests = spec.max_requests
            scrapers.append(scraper)
        except Exception as e:  # noqa: BLE001
            print(f"  [{spec.name}] builder error: {e}")
    return scrapers
