import re

from bs4 import BeautifulSoup

from src.profile import load_cv
from src.scrapers.base import BaseScraper, JobPost

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
JOB_PATH = re.compile(r"^/[a-z0-9][\w-]*/\d+$", re.IGNORECASE)


class Web3CareerScraper(BaseScraper):
    """Listado público de web3.career (RF-13, spec 002): HTML servido por el
    servidor, sin credenciales."""

    max_requests = 5

    def __init__(self, search_url: str | None = None):
        super().__init__("Web3Career")
        self.search_url = search_url or load_cv().get("platforms", {}).get(
            "web3career_search_url", "https://web3.career/remote-jobs"
        )

    def scrape(self, keywords: list[str]) -> list[JobPost]:
        resp = self.request(self.search_url, headers=UA, timeout=20)
        if resp is None or resp.status_code != 200:
            return []
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception:  # noqa: BLE001
            return []
        jobs = []
        seen = set()
        for row in soup.select("tr[data-jobid]"):
            job = self._parse_row(row, seen)
            if job:
                jobs.append(job)
        return self.filter_keyword_jobs(jobs, keywords)

    def _parse_row(self, row, seen: set) -> JobPost | None:
        link = row.select_one("a[href]")
        if not link:
            return None
        href = link.get("href", "")
        if not JOB_PATH.match(href):
            return None
        if href in seen:
            return None
        seen.add(href)

        title_el = row.select_one("h2, .job-title-truncate")
        company_el = row.select_one("h3")
        title = title_el.get_text(strip=True) if title_el else ""
        company = company_el.get_text(strip=True) if company_el else ""
        if not title:
            return None

        location = ""
        location_el = row.select_one(".job-location, .job-company-location")
        if location_el:
            location = location_el.get_text(" ", strip=True)
            if company and location.startswith(company):
                location = location[len(company):].strip()

        url = href if href.startswith("http") else f"https://web3.career{href}"
        combined = f"{title} {location}".lower()
        return JobPost(
            title=title, company=company, location=location or "Remote",
            description=title, url=url, source=self.name,
            is_remote="remote" in combined,
            apply_url=url, apply_button_active=True,
        )

    def verify_job_active(self, url: str) -> bool:
        resp = self.request(url, headers=UA, timeout=15)
        if resp is None:
            return True
        return resp.status_code == 200
