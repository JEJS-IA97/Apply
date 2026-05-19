import re
import requests
from datetime import datetime, timezone
from typing import List
from bs4 import BeautifulSoup
from src.scrapers.base import BaseScraper, JobPost

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


class WeWorkRemotelyScraper(BaseScraper):
    BASE = "https://weworkremotely.com"

    def __init__(self):
        super().__init__("WeWorkRemotely")

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        jobs = []
        categories = [
            "/categories/remote-full-stack-programming-jobs",
            "/categories/remote-front-end-programming-jobs",
            "/remote-qa-jobs",
        ]
        for cat in categories:
            try:
                resp = requests.get(
                    f"{self.BASE}{cat}",
                    headers={"User-Agent": UA, "Accept": "text/html"},
                    timeout=15
                )
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for article in soup.select("article"):
                    link = article.select_one("a[href*='/remote-jobs/'], a[href*='/listings/']")
                    if not link:
                        continue
                    href = link.get("href", "")
                    parts = href.split("/")
                    if len(parts) < 4 or not parts[-1]:
                        continue
                    title_el = article.select_one(".title, h2, h3, .job-title, .position, .listing-title")
                    company_el = article.select_one(".company, .subtitle, .company-name, .employer, .listing-company")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True) if company_el else ""
                    if not title:
                        continue
                    url = f"{self.BASE}{href}" if href.startswith("/") else href
                    jobs.append(JobPost(
                        title=title, company=company,
                        location="Remote", description="",
                        url=url, source=self.name,
                        posted_date=None, is_remote=True,
                        apply_url=url, apply_button_active=True
                    ))
            except Exception as e:
                print(f"  [WeWorkRemotely] category {cat}: {e}")
                continue
        return self.filter_keyword_jobs(jobs, keywords)

    def verify_job_active(self, url: str) -> bool:
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=10)
            if resp.status_code != 200:
                return False
            soup = BeautifulSoup(resp.text, "html.parser")
            text = resp.text.lower()
            if "no longer" in text or "filled" in text or "closed" in text:
                return False
            return bool(soup.select_one("[class*='apply']")) or "apply now" in text
        except Exception:
            return False
