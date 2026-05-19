import requests
from datetime import datetime, timezone
from typing import List
from src.scrapers.base import BaseScraper, JobPost


class RemoteOKScraper(BaseScraper):
    def __init__(self):
        super().__init__("RemoteOK")

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        try:
            resp = requests.get(
                "https://remoteok.com/api",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            if not isinstance(data, list) or len(data) < 2:
                return []
            jobs = []
            for item in data[1:]:
                job = self._parse(item)
                if job:
                    jobs.append(job)
            return self.filter_keyword_jobs(jobs, keywords)
        except Exception as e:
            print(f"  [RemoteOK] scrape error: {e}")
            return []

    def _parse(self, item: dict) -> JobPost:
        title = item.get("position", "")
        company = item.get("company", "")
        location = item.get("location", "Remote")
        desc = item.get("description", "")
        url = f"https://remoteok.com/remote-jobs/{item.get('slug', '')}"
        date_str = item.get("date")
        posted = None
        if date_str:
            try:
                posted = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
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
            return resp.status_code == 200 and "apply" in resp.text.lower()
        except Exception:
            return False
