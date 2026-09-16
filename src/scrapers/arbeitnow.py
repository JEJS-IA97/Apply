import requests
from datetime import datetime, timezone
from typing import List, Optional
from src.scrapers.base import BaseScraper, JobPost


class ArbeitnowScraper(BaseScraper):
    """Arbeitnow's public Job Board API: free, no key, no auth, no anti-bot wall.
    Docs: https://arbeitnow.com/blog/job-board-api/
    Mostly Europe/remote roles pulled from ATSs (Greenhouse, Recruitee, etc).
    """

    API = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self):
        super().__init__("Arbeitnow")

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        jobs = []
        try:
            page = 1
            while page <= 3:
                resp = requests.get(self.API, params={"page": page}, timeout=15)
                if resp.status_code != 200:
                    break
                data = resp.json()
                items = data.get("data", [])
                if not items:
                    break
                for item in items:
                    job = self._parse(item)
                    if job:
                        jobs.append(job)
                if not data.get("links", {}).get("next"):
                    break
                page += 1
        except Exception:
            pass
        return self.filter_keyword_jobs(jobs, keywords)

    def _parse(self, item: dict) -> Optional[JobPost]:
        title = item.get("title", "")
        company = item.get("company_name", "")
        location = item.get("location", "") or ("Remote" if item.get("remote") else "")
        desc = item.get("description", "") or ""
        url = item.get("url", "")
        is_remote = bool(item.get("remote"))
        ts = item.get("created_at")
        posted = None
        if ts:
            try:
                posted = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                posted = None
        return JobPost(
            title=title, company=company, location=location or "Remote",
            description=desc, url=url, source=self.name,
            posted_date=posted, is_remote=is_remote,
            apply_url=url, apply_button_active=True
        )

    def verify_job_active(self, url: str) -> bool:
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False
