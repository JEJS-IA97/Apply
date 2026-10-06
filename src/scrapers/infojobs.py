import re
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, JobPost

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
SEARCH_URL = "https://www.infojobs.net/ofertas-trabajo"
CARDS = "li.ij-List-item.ij-OfferList-offerCardItem"
TITLE = "h2.ij-OfferCardContent-description-title a"
COMPANY = "h3.ij-OfferCardContent-description-subtitle"
LOCATION = "ul.ij-OfferCardContent-description-list li"
DATE = "span.ij-FormatterSincedate"
DESCRIPTION = "p.ij-OfferCardContent-description-description"
OFFER_PATH = re.compile(r"^/[a-z0-9-]+/[a-z0-9-]+/of-i[0-9a-f]+$", re.IGNORECASE)


def _parse_since(text: str) -> datetime | None:
    """'Hace 8m' / 'Hace 2h' / 'Hace 3d' / 'Hace 1 semana' -> datetime UTC."""
    match = re.search(r"(\d+)\s*(m|min|hora|h|dia|d[ií]a|d|semana|s)", (text or "").lower())
    if not match:
        return None
    qty = int(match.group(1))
    unit = match.group(2)
    if unit in ("m", "min"):
        delta = timedelta(minutes=qty)
    elif unit in ("h", "hora"):
        delta = timedelta(hours=qty)
    elif unit.startswith("d") or unit in ("d",):
        delta = timedelta(days=qty)
    else:
        delta = timedelta(weeks=qty)
    return datetime.now(timezone.utc) - delta


class InfoJobsScraper(BaseScraper):
    """Ofertas en español de InfoJobs (RF-13, spec 002): listado
    server-rendered con fecha explícita ('Hace Xm'), sin credenciales."""

    trusts_freshness = True
    max_requests = 5

    def __init__(self, search_url: str = SEARCH_URL):
        super().__init__("InfoJobs")
        self.search_url = search_url

    def scrape(self, keywords: list[str]) -> list[JobPost]:
        resp = self.request(self.search_url, headers={"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"}, timeout=25)
        if resp is None or resp.status_code != 200:
            return []
        if "captcha" in resp.text.lower():
            self.disabled_reason = "InfoJobs respondió con captcha anti-bot"
            print(f"  [InfoJobs] DETENIDA: {self.disabled_reason}")
            return []
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception:  # noqa: BLE001
            return []
        jobs = []
        seen = set()
        for card in soup.select(CARDS):
            job = self._parse_card(card, seen)
            if job:
                jobs.append(job)
        if not jobs:
            print("  [InfoJobs] 0 tarjetas parseadas (anti-bot o variante de pagina)")
        return self.filter_keyword_jobs(jobs, keywords)

    def _parse_card(self, card, seen: set) -> JobPost | None:
        link = card.select_one(TITLE)
        if not link:
            return None
        href = (link.get("href") or "").split("?")[0].strip()
        if not href:
            return None
        if href.startswith("//"):
            href = f"https:{href}"
        path = re.sub(r"https?://[^/]+", "", href)
        if not OFFER_PATH.match(path):
            return None
        if href in seen:
            return None
        seen.add(href)

        title = link.get_text(" ", strip=True)
        if not title:
            return None
        company_el = card.select_one(COMPANY)
        company = company_el.get_text(" ", strip=True) if company_el else ""

        items = card.select(f"{LOCATION} > *")
        location = items[0].get_text(" ", strip=True) if items else ""
        work_mode = items[1].get_text(" ", strip=True) if len(items) > 1 else ""

        date_el = card.select_one(DATE)
        posted = _parse_since(date_el.get_text(" ", strip=True)) if date_el else None

        desc_el = card.select_one(DESCRIPTION)
        description = desc_el.get_text(" ", strip=True) if desc_el else ""

        lowered = f"{title} {location} {work_mode}".lower()
        is_remote = any(s in lowered for s in ("remoto", "teletrabajo", "remote", "flexible"))
        return JobPost(
            title=title, company=company, location=location or work_mode,
            description=description[:1500], url=href, source=self.name,
            posted_date=posted, is_remote=is_remote, apply_url=href,
            apply_button_active=True,
        )

    def verify_job_active(self, url: str) -> bool:
        resp = self.request(url, headers={"User-Agent": UA}, timeout=15)
        if resp is None:
            return True
        return resp.status_code == 200
