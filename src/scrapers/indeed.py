import requests
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import quote
from bs4 import BeautifulSoup
from src.scrapers.base import BaseScraper, JobPost


class IndeedScraper(BaseScraper):
    BASE = "https://www.indeed.com"

    def __init__(self):
        super().__init__("Indeed")

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        jobs = []
        for kw in self.unique_keywords(keywords):
            try:
                params = {
                    "q": kw,
                    "l": "remote",
                    "sc": "0kf:attr(DSQF7);",
                    "fromage": "7",
                    "sort": "date"
                }
                resp = requests.get(
                    f"{self.BASE}/jobs",
                    params=params,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    timeout=20
                )
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for card in soup.select("[class*='job_seen_beacon'], .jobCard"):
                    job = self._parse_card(card)
                    if job:
                        jobs.append(job)
            except Exception:
                continue
        return self.filter_keyword_jobs(jobs, keywords)

    def _parse_card(self, card) -> Optional[JobPost]:
        title_el = card.select_one("[id*='jobTitle'], h2 a, .jobTitle")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        link = title_el if title_el.name == "a" else title_el.select_one("a")
        href = link.get("href", "") if link else ""
        if href and not href.startswith("http"):
            href = f"{self.BASE}{href}"
        company_el = card.select_one("[data-testid='companyName'], .companyName")
        company = company_el.get_text(strip=True) if company_el else ""
        location_el = card.select_one("[data-testid='text-location'], .companyLocation")
        location = location_el.get_text(strip=True) if location_el else ""
        date_el = card.select_one("[data-testid='job-date'], .date")
        posted = None
        if date_el:
            text = date_el.get_text(strip=True).lower()
            if "today" in text or "just posted" in text:
                posted = datetime.now(timezone.utc)
            elif "day" in text:
                match = re.search(r'(\d+)', text)
                if match:
                    posted = datetime.now(timezone.utc) - timedelta(days=int(match.group(1)))
        desc_el = card.select_one(".job-snippet, [data-testid='job-snippet']")
        desc = desc_el.get_text(strip=True) if desc_el else ""
        return JobPost(
            title=title, company=company, location=location,
            description=desc, url=href, source=self.name,
            posted_date=posted, is_remote="remote" in location.lower(),
            apply_url=href, apply_button_active=True
        )

    def verify_job_active(self, url: str) -> bool:
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if resp.status_code != 200:
                return False
            text = resp.text.lower()
            if "no longer accepting" in text or "position filled" in text:
                return False
            return "apply" in text or "apply now" in text
        except Exception:
            return False
