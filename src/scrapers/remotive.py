import requests
from datetime import datetime, timezone
from typing import List
from src.scrapers.base import BaseScraper, JobPost


class RemotiveScraper(BaseScraper):
    def __init__(self):
        super().__init__("Remotive")

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        jobs = []
        categories = ["software-dev", "qa", "front-end"]
        for cat in categories:
            try:
                resp = requests.get(
                    f"https://remotive.com/api/remote-jobs?category={cat}",
                    timeout=15
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for item in data.get("jobs", []):
                    job = self._parse(item)
                    if job:
                        jobs.append(job)
            except Exception:
                continue
        return self.filter_keyword_jobs(jobs, keywords)

    def _parse(self, item: dict) -> JobPost:
        title = item.get("title", "")
        company = item.get("company_name", "")
        location = item.get("candidate_required_location", "Remote")
        desc = item.get("description", "")
        url = item.get("url", "")
        date_str = item.get("publication_date")
        posted = None
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                posted = dt
            except (ValueError, AttributeError):
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
