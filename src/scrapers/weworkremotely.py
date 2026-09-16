import re
import requests
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional
from xml.etree import ElementTree
from bs4 import BeautifulSoup
from src.scrapers.base import BaseScraper, JobPost

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


class WeWorkRemotelyScraper(BaseScraper):
    """Uses WWR's public per-category RSS feeds instead of scraping HTML.

    WWR's job listing pages are protected by Cloudflare and their markup
    changes periodically, which silently breaks CSS-selector scraping
    (returns 0 jobs with no error). The RSS feeds are officially published,
    stable, and explicitly sanctioned for this kind of use:
    https://weworkremotely.com/remote-job-rss-feed
    """

    BASE = "https://weworkremotely.com"
    FEEDS = [
        "/categories/remote-programming-jobs.rss",
        "/categories/remote-devops-sysadmin-jobs.rss",
        "/categories/all-other-remote-jobs.rss",
    ]

    def __init__(self):
        super().__init__("WeWorkRemotely")

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        jobs = []
        for feed in self.FEEDS:
            try:
                resp = requests.get(
                    f"{self.BASE}{feed}",
                    headers={"User-Agent": UA, "Accept": "application/rss+xml, text/xml"},
                    timeout=15
                )
                if resp.status_code != 200:
                    continue
                root = ElementTree.fromstring(resp.content)
                for item in root.findall("./channel/item"):
                    job = self._parse_item(item)
                    if job:
                        jobs.append(job)
            except (requests.RequestException, ElementTree.ParseError) as e:
                print(f"  [WeWorkRemotely] feed {feed}: {e}")
                continue
        return self.filter_keyword_jobs(jobs, keywords)

    def _parse_item(self, item) -> Optional[JobPost]:
        raw_title = (item.findtext("title") or "").strip()
        if not raw_title:
            return None

        if ":" in raw_title:
            company, title = raw_title.split(":", 1)
            company, title = company.strip(), title.strip()
        else:
            company, title = "", raw_title

        link = (item.findtext("link") or "").strip()
        region = (item.findtext("region") or "Remote").strip()

        raw_desc = item.findtext("description") or ""
        desc_soup = BeautifulSoup(raw_desc, "html.parser")

        location = region
        hq_strong = desc_soup.find(
            lambda tag: tag.name == "strong" and "headquarters" in tag.get_text(strip=True).lower()
        )
        if hq_strong and hq_strong.parent is not None:
            parent_text = hq_strong.parent.get_text(" ", strip=True)
            hq_value = re.sub(r"(?i)headquarters:\s*", "", parent_text, count=1).strip()
            if hq_value:
                location = hq_value

        description = desc_soup.get_text(separator=" ", strip=True)

        pub_date = item.findtext("pubDate")
        posted = None
        if pub_date:
            try:
                posted = parsedate_to_datetime(pub_date)
                if posted.tzinfo is None:
                    posted = posted.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                posted = None

        return JobPost(
            title=title, company=company, location=location,
            description=description, url=link, source=self.name,
            posted_date=posted, is_remote=True,
            apply_url=link, apply_button_active=True
        )

    def verify_job_active(self, url: str) -> bool:
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=10)
            if resp.status_code != 200:
                return False
            text = resp.text.lower()
            if "no longer" in text or "filled" in text or "closed" in text:
                return False
            soup = BeautifulSoup(resp.text, "html.parser")
            return bool(soup.select_one("[class*='apply']")) or "apply now" in text
        except Exception:
            return False
