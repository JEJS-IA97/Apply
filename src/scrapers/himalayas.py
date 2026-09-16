import requests
from datetime import datetime, timezone
from typing import List, Optional
from src.scrapers.base import BaseScraper, JobPost


class HimalayasScraper(BaseScraper):
    """Himalayas' public remote-jobs feed: free, no key, no auth.
    Docs/behavior: GET https://himalayas.app/jobs/api?limit=20&offset=0
    Every listing on Himalayas is verified remote, so is_remote is always True.
    """

    API = "https://himalayas.app/jobs/api"
    PAGE_SIZE = 20
    MAX_PAGES = 5

    def __init__(self):
        super().__init__("Himalayas")

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        jobs = []
        try:
            for page in range(self.MAX_PAGES):
                resp = requests.get(
                    self.API,
                    params={"limit": self.PAGE_SIZE, "offset": page * self.PAGE_SIZE},
                    timeout=15
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                items = data.get("jobs", [])
                if not items:
                    break
                for item in items:
                    job = self._parse(item)
                    if job:
                        jobs.append(job)
                if len(items) < self.PAGE_SIZE:
                    break
        except Exception:
            pass
        return self.filter_keyword_jobs(jobs, keywords)

    def _parse(self, item: dict) -> Optional[JobPost]:
        title = item.get("title", "")
        company = item.get("companyName", "") or item.get("company", "")
        restrictions = item.get("locationRestrictions") or []
        location = ", ".join(restrictions) if restrictions else "Remote (Worldwide)"
        desc = item.get("excerpt", "") or item.get("description", "") or ""
        url = item.get("applicationLink") or item.get("guid", "")
        ts = item.get("pubDate") or item.get("publishedDate")
        posted = None
        if ts:
            try:
                posted = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                posted = None
        return JobPost(
            title=title, company=company, location=location,
            description=desc, url=url, source=self.name,
            posted_date=posted, is_remote=True,
            apply_url=url, apply_button_active=True
        )

    def verify_job_active(self, url: str) -> bool:
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False
