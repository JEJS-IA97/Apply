import json
import re
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, JobPost

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
SEARCH_URL = "https://builtin.com/jobs?search=remote"
JOB_PATH = re.compile(r"^/job/[a-z0-9-]+/(\d+)$", re.IGNORECASE)


def _parse_relative_date(text: str, base: datetime | None = None) -> datetime | None:
    lowered = (text or "").lower()
    now = base or datetime.now(timezone.utc)
    match = re.search(r"(\d+)\s*minute", lowered)
    if match:
        return now - timedelta(minutes=int(match.group(1)))
    match = re.search(r"(\d+)\s*hour", lowered)
    if match:
        return now - timedelta(hours=int(match.group(1)))
    match = re.search(r"(\d+)\s*day", lowered)
    if match:
        return now - timedelta(days=int(match.group(1)))
    return None


class BuiltInScraper(BaseScraper):
    """Listado de Built In (RF-13, spec 002): el servidor incluye un JSON-LD
    ItemList con título, URL y descripción de cada oferta."""

    max_requests = 3

    def __init__(self, search_url: str = SEARCH_URL):
        super().__init__("BuiltIn")
        self.search_url = search_url

    def scrape(self, keywords: list[str]) -> list[JobPost]:
        resp = self.request(self.search_url, headers={"User-Agent": UA}, timeout=25)
        if resp is None or resp.status_code != 200:
            return []
        jobs: list[JobPost] = []
        for item in self._json_ld_items(resp.text):
            job = self._parse_item(item)
            if job:
                jobs.append(job)
        if not jobs:
            jobs = self._parse_cards(resp.text)
        return self.filter_keyword_jobs(jobs, keywords)

    def _json_ld_items(self, html: str) -> list[dict]:
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:  # noqa: BLE001
            return []
        items: list[dict] = []
        for script in soup.select("script[type='application/ld+json']"):
            try:
                data = json.loads(script.string or "")
            except (ValueError, TypeError):
                continue
            graph = data.get("@graph", []) if isinstance(data, dict) else []
            for node in graph:
                if isinstance(node, dict) and node.get("@type") == "ItemList":
                    items.extend(node.get("itemListElement", []))
        return [i for i in items if isinstance(i, dict)]

    def _parse_item(self, item: dict) -> JobPost | None:
        url = item.get("url") or ""
        title = item.get("name") or ""
        if not url or not title:
            return None
        if not JOB_PATH.match(re.sub(r"https?://[^/]+", "", url)):
            return None
        description = (item.get("description") or "")[:1500]
        return JobPost(
            title=title, company="", location="Remote",
            description=description, url=url, source=self.name,
            posted_date=None, is_remote=True, apply_url=url,
        )

    def _parse_cards(self, html: str) -> list[JobPost]:
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:  # noqa: BLE001
            return []
        jobs = []
        for link in soup.select("a[href^='/job/']"):
            href = link.get("href", "").split("?")[0]
            if not JOB_PATH.match(href):
                continue
            title = link.get_text(" ", strip=True)
            if not title or len(title) > 200:
                continue
            date_el = link.select_one("time, [class*='date']")
            posted = _parse_relative_date(date_el.get_text(" ", strip=True)) if date_el else None
            jobs.append(JobPost(
                title=title, company="", location="Remote",
                description="", url=f"https://builtin.com{href}", source=self.name,
                posted_date=posted, is_remote=True, apply_url=f"https://builtin.com{href}",
            ))
        return jobs

    def verify_job_active(self, url: str) -> bool:
        resp = self.request(url, headers={"User-Agent": UA}, timeout=15)
        if resp is None:
            return True
        return resp.status_code == 200
