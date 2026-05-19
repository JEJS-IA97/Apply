import requests
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from bs4 import BeautifulSoup
from src.scrapers.base import BaseScraper, JobPost


class GetOnBoardScraper(BaseScraper):
    BASE = "https://www.getonbrd.com"

    def __init__(self):
        super().__init__("GetOnBoard")

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        jobs = []
        for kw in self.unique_keywords(keywords):
            try:
                resp = requests.get(
                    f"{self.BASE}/search",
                    params={"q": f"{kw} remote"},
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15
                )
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for card in soup.select("[class*='JobCard'], [class*='job-card'], .job-tile"):
                    job = self._parse_card(card)
                    if job:
                        jobs.append(job)
            except Exception:
                continue
        return self.filter_keyword_jobs(jobs, keywords)

    def _parse_card(self, card) -> Optional[JobPost]:
        link_el = card.select_one("a[href*='/jobs/'], a[href*='/empleos/']")
        if not link_el:
            return None
        href = link_el.get("href", "")
        if href and not href.startswith("http"):
            href = f"{self.BASE}{href}"
        title_el = card.select_one("[class*='title'], h2, h3")
        title = title_el.get_text(strip=True) if title_el else ""
        company_el = card.select_one("[class*='company'], [class*='org']")
        company = company_el.get_text(strip=True) if company_el else ""
        location_el = card.select_one("[class*='location'], [data-test='location']")
        location = location_el.get_text(strip=True) if location_el else ""
        desc_el = card.select_one("p, [class*='description'], [class*='desc']")
        desc = desc_el.get_text(strip=True) if desc_el else ""
        return JobPost(
            title=title, company=company, location=location,
            description=desc, url=href, source=self.name,
            posted_date=datetime.now(timezone.utc), is_remote="remote" in location.lower(),
            apply_url=href, apply_button_active=True
        )

    def verify_job_active(self, url: str) -> bool:
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if resp.status_code != 200:
                return False
            soup = BeautifulSoup(resp.text, "html.parser")
            text = resp.text.lower()
            if "not available" in text or "closed" in text:
                return False
            return bool(soup.select_one("[class*='apply'], [class*='postular'], a[href*='apply']")) or "apply" in text
        except Exception:
            return False
