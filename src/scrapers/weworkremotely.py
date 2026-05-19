import re
import requests
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from src.scrapers.base import BaseScraper, JobPost


class WeWorkRemotelyScraper(BaseScraper):
    BASE = "https://weworkremotely.com"

    def __init__(self):
        super().__init__("WeWorkRemotely")

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        jobs = []
        categories = [
            "/remote-jobs/design",
            "/remote-jobs/devops-sysadmin",
            "/remote-jobs/full-stack-programming",
            "/remote-jobs/front-end-programming",
            "/remote-jobs/qa",
        ]
        for cat in categories:
            try:
                resp = requests.get(f"{self.BASE}{cat}", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for li in soup.select("li"):
                    link = li.select_one("a")
                    if not link or not link.get("href"):
                        continue
                    href = link["href"]
                    if not href.startswith("/remote-jobs"):
                        continue
                    title_el = li.select_one(".title")
                    company_el = li.select_one(".company")
                    if not title_el or not company_el:
                        continue
                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True)
                    url = f"{self.BASE}{href}"
                    posted = self._extract_date(li)
                    jobs.append(JobPost(
                        title=title, company=company,
                        location="Remote", description="",
                        url=url, source=self.name,
                        posted_date=posted, is_remote=True,
                        apply_url=url, apply_button_active=True
                    ))
            except Exception:
                continue
        return jobs

    def _extract_date(self, li) -> datetime:
        time_el = li.select_one("time")
        if time_el and time_el.get("datetime"):
            try:
                return datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
            except ValueError:
                pass
        return None

    def verify_job_active(self, url: str) -> bool:
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if resp.status_code != 200:
                return False
            soup = BeautifulSoup(resp.text, "html.parser")
            return bool(soup.select_one(".apply_button") or "apply" in resp.text.lower())
        except Exception:
            return False
