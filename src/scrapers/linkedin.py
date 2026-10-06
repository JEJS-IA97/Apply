import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from src.profile import load_cv
from src.scrapers.base import BaseScraper, JobPost

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
GUEST_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
VIEW_URL = "https://www.linkedin.com/jobs/view/{job_id}"

DEFAULT_TERMS = ["QA Automation", "QA Engineer", "Frontend Developer", "React Developer"]
DEFAULT_LOCATIONS = ["Latin America", "Remote"]


def extract_job_id(html_or_url: str) -> str | None:
    """RF-14 (spec 002): el guest API devuelve `urn:li:jobPosting:{id}` y URLs
    slug (`/jobs/view/titulo-at-empresa-{id}`); el id numérico viejo
    (`/jobs/view/{id}`) ya no aparece."""
    match = re.search(r"jobPosting:(\d+)", html_or_url or "")
    if match:
        return match.group(1)
    match = re.search(r"/jobs/view/([^?\"'\s]+)", html_or_url or "")
    if match:
        slug = match.group(1)
        tail = re.search(r"(\d{5,})$", slug.rstrip("/"))
        if tail:
            return tail.group(1)
    match = re.search(r"-(\d{5,})(?:\?|$)", html_or_url or "")
    if match:
        return match.group(1)
    return None


class LinkedInScraper(BaseScraper):
    trusts_freshness = True
    max_requests = 40

    def __init__(self, email: str = "", password: str = ""):
        super().__init__("LinkedIn")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self.logged_in = False
        if email and password:
            self._login(email, password)

    def _login(self, email, password):
        try:
            resp = self.session.get("https://www.linkedin.com/login", timeout=15)
            if resp.status_code != 200:
                return
            soup = BeautifulSoup(resp.text, "html.parser")
            csrf = soup.select_one("input[name=loginCsrfParam]")
            csrf_value = csrf.get("value", "") if csrf else ""
            resp2 = self.session.post(
                "https://www.linkedin.com/checkpoint/lg/login-submit",
                data={"session_key": email, "session_password": password, "loginCsrfParam": csrf_value},
                headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": "https://www.linkedin.com", "Referer": "https://www.linkedin.com/login"},
                timeout=20, allow_redirects=True
            )
            self.logged_in = "li_at" in self.session.cookies or "login" not in resp2.url.lower()
            if self.logged_in:
                print("  [LinkedIn] Logged in")
            else:
                print("  [LinkedIn] Login failed")
        except Exception as e:  # noqa: BLE001
            print(f"  [LinkedIn] Login error: {e}")

    def scrape(self, keywords: list[str]) -> list[JobPost]:
        return self._search()

    def _search_terms(self) -> list[tuple]:
        platforms = load_cv().get("platforms", {})
        terms = platforms.get("linkedin_search_terms") or DEFAULT_TERMS
        locations = platforms.get("linkedin_locations") or DEFAULT_LOCATIONS
        chosen_locations = [loc for loc in locations if loc in ("Latin America", "Remote")] or locations[:2]
        return [(term, loc) for term in terms[:12] for loc in chosen_locations[:2]]

    def _search(self) -> list[JobPost]:
        jobs: list[JobPost] = []
        seen = set()
        window_days = max(1, self._max_days_old())
        params_base = {"f_WT": "2", "f_TPR": f"r{window_days * 86400}"}

        for kw, loc in self._search_terms():
            if self.requests_made >= self.max_requests:
                break
            try:
                params = {"keywords": kw, "location": loc, "start": 0, **params_base}
                resp = self.request(GUEST_API, params=params, timeout=20, headers={
                    "User-Agent": UA, "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
                })
                if resp is None or resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for card in soup.select("li"):
                    job = self._parse_card(card, seen)
                    if job:
                        jobs.append(job)
            except Exception:  # noqa: BLE001, S112
                continue
        return jobs

    @staticmethod
    def _max_days_old() -> int:
        try:
            from src.config import config
            return config.max_days_old
        except Exception:  # noqa: BLE001
            return 7

    def _parse_card(self, card, seen: set) -> JobPost | None:
        link = card.select_one("a.base-card__full-link")
        if not link:
            return None
        href = link.get("href", "")
        job_id = extract_job_id(card.get("data-entity-urn") or "") or extract_job_id(href)
        if not job_id or job_id in seen:
            return None
        seen.add(job_id)

        title_el = card.select_one("h3.base-search-card__title")
        company_el = card.select_one("h4.base-search-card__subtitle")
        location_el = card.select_one(".job-search-card__location")
        time_el = card.select_one("time")
        title = title_el.get_text(strip=True) if title_el else ""
        company = company_el.get_text(strip=True) if company_el else ""
        location = location_el.get_text(strip=True) if location_el else ""
        if not title:
            return None

        posted = None
        if time_el and time_el.get("datetime"):
            try:
                posted = datetime.strptime(time_el["datetime"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                posted = None

        url = VIEW_URL.format(job_id=job_id)
        is_remote = any(r in location.lower() for r in ["remote", "remoto", "worldwide", "global", "distributed", "latam"])
        return JobPost(
            title=title, company=company, location=location,
            description="", url=url, source=self.name,
            posted_date=posted, is_remote=is_remote, apply_url=url,
        )

    def enrich(self, job: JobPost) -> bool | None:
        """RF-12 (spec 001): obtiene la descripción con la misma petición de
        detalle. Devuelve True si la completó, False si la oferta ya no
        existe y None si no hubo cambio."""
        if job.description:
            return None
        job_id = extract_job_id(job.url)
        if not job_id:
            return None
        try:
            resp = self.request(VIEW_URL.format(job_id=job_id), timeout=15, headers={"User-Agent": UA})
        except requests.RequestException:
            return None
        if resp is None:
            return None
        if resp.status_code in (404, 410):
            return False
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        markup = soup.select_one(".show-more-less-html__markup, #job-details")
        if markup:
            text = re.sub(r"\s+", " ", markup.get_text(" ", strip=True)).strip()
            if text:
                job.description = text
                return True
        return None

    def verify_job_active(self, url: str) -> bool:
        try:
            resp = self.session.get(url, timeout=15, allow_redirects=True)
            if resp.status_code in (404, 410):
                return False
            if resp.status_code != 200:
                return False
            text = resp.text.lower()
            if "this position has been filled" in text or "no longer accepting" in text:
                return False
            return not ("job search" in text and len(text) < 2000)
        except Exception:  # noqa: BLE001
            return False
