"""RF-7 (spec 004): Get on Board vía su API pública.

GET https://www.getonbrd.com/api/v0/search/jobs?query=<q>&per_page=50&expand=["company"]
Solo se conservan ofertas `fully_remote` (trabajables desde cualquier país) y de
nivel hasta semi-senior (seniority id <= 3).
"""
import re
from datetime import UTC, datetime

import requests

from src.scrapers.base import BaseScraper, JobPost

API = "https://www.getonbrd.com/api/v0/search/jobs"
UA = "Mozilla/5.0 (job-bot; +https://github.com/JEJS-IA97/Apply)"


def _strip(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


class GetOnBoardScraper(BaseScraper):
    trusts_freshness = True
    max_requests = 12

    def __init__(self):
        super().__init__("GetOnBoard")

    def scrape(self, keywords: list[str]) -> list[JobPost]:
        jobs: dict[str, JobPost] = {}
        for kw in self.unique_keywords(keywords):
            try:
                resp = self.request(
                    API, params={"query": kw, "per_page": 50, "expand": '["company"]'},
                    headers={"User-Agent": UA}, timeout=20,
                )
            except requests.RequestException:
                break
            if resp is None:
                break
            if resp.status_code != 200:
                continue
            try:
                items = resp.json().get("data", [])
            except ValueError:
                continue
            for item in items:
                job = self.parse_item(item)
                if job and job.url not in jobs:
                    jobs[job.url] = job
        return self.filter_keyword_jobs(list(jobs.values()), keywords)

    @staticmethod
    def parse_item(item: dict) -> JobPost | None:
        a = item.get("attributes") or {}
        if not a.get("remote") or a.get("remote_modality") != "fully_remote":
            return None
        seniority = ((a.get("seniority") or {}).get("data") or {}).get("id")
        if seniority and int(seniority) >= 4:
            return None
        company = ((((a.get("company") or {}).get("data") or {}).get("attributes")) or {}).get("name", "")
        description = " ".join(_strip(a.get(k, "")) for k in ("description", "functions", "desirable", "benefits"))
        salary = None
        if a.get("min_salary") or a.get("max_salary"):
            salary = f"{a.get('min_salary') or ''}-{a.get('max_salary') or ''} USD/mes"
        posted = None
        if a.get("published_at"):
            posted = datetime.fromtimestamp(int(a["published_at"]), tz=UTC)
        url = (item.get("links") or {}).get("public_url") or ""
        if not url or not a.get("title"):
            return None
        return JobPost(
            title=a["title"], company=company, location="Remote (Worldwide)",
            description=description, url=url, source="GetOnBoard",
            posted_date=posted, is_remote=True, apply_url=url, salary=salary,
        )

    def verify_job_active(self, url: str) -> bool:
        return True
