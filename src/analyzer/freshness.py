"""RF-15 (spec 004): comprueba que las publicaciones (LinkedIn, Telegram,
Mastodon…) sean recientes y que la oferta a la que enlazan siga abierta."""
import json
import re
from datetime import UTC, datetime, timedelta

import requests

from src.scrapers.base import JobPost

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
CLOSED_RE = re.compile(
    r"(no longer accepting applications|no longer available|this (job|position|role) (has been|is) "
    r"(filled|closed)|(job|position|posting) (is |has )?(closed|expired)|position (has been )?filled|"
    r"applications? (are |is )?(now )?closed|vacante (cerrada|cubierta|finalizada)|convocatoria cerrada|"
    r"cerramos la convocatoria|ya no (se )?acepta|oferta (cerrada|caducada|expirada|finalizada|no disponible)|"
    r"b[uú]squeda (venci[oó]|cerrada|finalizada)|proceso (de selecci[oó]n )?cerrado)",
    re.IGNORECASE,
)
JSONLD_RE = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.IGNORECASE | re.DOTALL)
SKIP_HOSTS = ("t.me/", "linkedin.com/search", "linkedin.com/feed", "lnkd.in/", "wa.me/", "mailto:")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        d = datetime.fromisoformat(str(value).strip())
    except ValueError:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", str(value))
        if not m:
            return None
        d = datetime.fromisoformat(m.group(1))
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _job_postings(html: str) -> list[dict]:
    found = []
    for block in JSONLD_RE.findall(html):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                if item.get("@type") == "JobPosting":
                    found.append(item)
                stack.extend(v for v in item.values() if isinstance(v, (list, dict)))
            elif isinstance(item, list):
                stack.extend(item)
    return found


def check_page(html: str, status: int, now: datetime, max_age_days: int) -> tuple[str, datetime | None]:
    """Devuelve (motivo de exclusión o "", fecha de publicación encontrada)."""
    if status in (404, 410):
        return "oferta_cerrada", None
    posted = None
    for jp in _job_postings(html):
        valid = _parse_date(jp.get("validThrough"))
        if valid and valid < now:
            return "oferta_cerrada", None
        posted = _parse_date(jp.get("datePosted")) or posted
    if CLOSED_RE.search(re.sub(r"<[^>]+>", " ", html)):
        return "oferta_cerrada", posted
    if posted and now - posted > timedelta(days=max_age_days):
        return "publicacion_vieja", posted
    return "", posted


def verify_freshness(jobs: list[JobPost], max_age_days: int = 14, max_checks: int = 40,
                     session: requests.Session | None = None, now: datetime | None = None,
                     ) -> tuple[list[JobPost], list[tuple[JobPost, str]]]:
    """Excluye publicaciones viejas o cerradas. Solo abre el enlace de las que
    vienen de posts (post_source); si el enlace no responde, la oferta se queda."""
    now = now or datetime.now(UTC)
    session = session or requests.Session()
    kept, excluded, checks = [], [], 0
    for job in jobs:
        reason = ""
        if job.posted_date:
            posted = job.posted_date if job.posted_date.tzinfo else job.posted_date.replace(tzinfo=UTC)
            if now - posted > timedelta(days=max_age_days):
                reason = "publicacion_vieja"
        if not reason and job.post_source and CLOSED_RE.search(job.description or ""):
            reason = "oferta_cerrada"
        link = job.apply_url or job.url
        if (not reason and job.post_source and link and link.startswith("http")
                and not any(h in link for h in SKIP_HOSTS) and checks < max_checks):
            checks += 1
            try:
                resp = session.get(link, timeout=15, headers={"User-Agent": UA}, allow_redirects=True)
                reason, posted = check_page(resp.text[:400_000], resp.status_code, now, max_age_days)
                if posted and not job.posted_date:
                    job.posted_date = posted
            except requests.RequestException:
                reason = ""
        if reason:
            job.excluded_reason = reason
            excluded.append((job, reason))
        else:
            kept.append(job)
    return kept, excluded
