import requests
import re
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import quote
from src.scrapers.base import BaseScraper, JobPost


class LinkedInScraper(BaseScraper):
    SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    def __init__(self, cookies: Optional[dict] = None):
        super().__init__("LinkedIn")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        if cookies:
            for k, v in cookies.items():
                self.session.cookies.set(k, v)

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        jobs = []
        for kw in keywords[:5]:
            try:
                params = {
                    "keywords": kw,
                    "location": "Worldwide",
                    "f_WT": "2",
                    "f_TPR": "r604800",
                    "start": 0,
                }
                resp = self.session.get(
                    self.SEARCH_URL,
                    params=params,
                    timeout=20
                )
                if resp.status_code != 200:
                    continue
                jobs.extend(self._parse_list(resp.text, kw))
            except Exception:
                continue
        return jobs

    def _parse_list(self, html: str, keyword: str) -> List[JobPost]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for card in soup.select("li"):
            link = card.select_one("a.base-card__full-link")
            if not link:
                continue
            href = link.get("href", "")
            job_id = self._extract_job_id(href)
            if not job_id:
                continue
            title_el = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle")
            location_el = card.select_one(".job-search-card__location")
            time_el = card.select_one("time.job-search-card__listdate")
            title = title_el.get_text(strip=True) if title_el else ""
            company = company_el.get_text(strip=True) if company_el else ""
            location = location_el.get_text(strip=True) if location_el else ""
            posted = None
            if time_el and time_el.get("datetime"):
                try:
                    posted = datetime.fromisoformat(time_el["datetime"])
                except ValueError:
                    pass
            jobs.append(JobPost(
                title=title, company=company, location=location,
                description="", url=href, source=self.name,
                posted_date=posted, is_remote="remote" in location.lower(),
                apply_url=href, apply_button_active=False
            ))
        return jobs

    def _extract_job_id(self, url: str) -> Optional[str]:
        match = re.search(r'/jobs/view/(\d+)', url)
        return match.group(1) if match else None

    def verify_job_active(self, url: str) -> bool:
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return False
            text = resp.text.lower()
            if "this position has been filled" in text or "no longer accepting" in text:
                return False
            if "apply" in text or "solicitar" in text or "easy apply" in text:
                return True
            return "apply" in text
        except Exception:
            return False
