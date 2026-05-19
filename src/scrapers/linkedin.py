import re
from datetime import datetime, timezone
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup

from src.profile import profile
from src.scrapers.base import BaseScraper, JobPost

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


class LinkedInScraper(BaseScraper):
    SEARCH_LOCATIONS = [
        "Latin America",
        "Remote",
    ]
    GUEST_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    LOGGED_IN_SEARCH = "https://www.linkedin.com/jobs/search/"

    def __init__(self, email: str = "", password: str = ""):
        super().__init__("LinkedIn")
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self.logged_in = False
        if email and password:
            self._login()

    def _login(self):
        try:
            resp = self.session.get("https://www.linkedin.com/login", timeout=15)
            if resp.status_code != 200:
                return

            soup = BeautifulSoup(resp.text, "html.parser")
            csrf = soup.select_one("input[name=loginCsrfParam]")
            csrf_value = csrf.get("value", "") if csrf else ""
            payload = {
                "session_key": self.email,
                "session_password": self.password,
                "loginCsrfParam": csrf_value,
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://www.linkedin.com",
                "Referer": "https://www.linkedin.com/login",
            }
            resp2 = self.session.post(
                "https://www.linkedin.com/checkpoint/lg/login-submit",
                data=payload,
                headers=headers,
                timeout=20,
                allow_redirects=True,
            )
            self.logged_in = "li_at" in self.session.cookies or "login" not in resp2.url.lower()
            if self.logged_in:
                print("  [LinkedIn] Logged in successfully")
            else:
                print("  [LinkedIn] Login failed (may need CAPTCHA)")
        except Exception as e:
            print(f"  [LinkedIn] Login error: {e}")

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        search_pairs = self._build_search_pairs(keywords)
        if self.logged_in:
            jobs = self._scrape_logged_in(search_pairs)
            if jobs:
                return self.filter_keyword_jobs(jobs, keywords)
            print("  [LinkedIn] Logged-in search returned 0 jobs, falling back to guest endpoint")
        return self.filter_keyword_jobs(self._scrape_guest(search_pairs), keywords)

    def _build_search_pairs(self, keywords: List[str]) -> List[Tuple[str, str]]:
        search_terms = self.unique_keywords(keywords)
        if not search_terms:
            search_terms = [
                "QA Automation Engineer",
                "QA Engineer",
                "Frontend Developer",
                "React Developer",
                "SDET",
                "QA",
                "QA Analyst",
                "Tester",
                "Tester QA",
                "QA Analista",
                "Functional Tester",
                "Manual QA",
                "Quality Assurance Analyst",
                "Quality Assurance",
                "Ingeniero de QA Automatizador",
                "Functional Tester",
                "Cypress",
                "Playwright",
                "Pytest",
                "Selenium",
            ]

        locations = []
        for location in self.SEARCH_LOCATIONS + [profile.location]:
            cleaned = " ".join((location or "").split())
            if cleaned and cleaned not in locations:
                locations.append(cleaned)

        return [(keyword, location) for keyword in search_terms for location in locations]

    def _scrape_logged_in(self, search_pairs: List[Tuple[str, str]]) -> List[JobPost]:
        jobs = []
        seen_ids = set()
        for kw, loc in search_pairs:
            try:
                params = {
                    "keywords": kw,
                    "location": loc,
                    "f_WT": "2",
                    "f_TPR": "r86400",
                    "start": 0,
                }
                resp = self.session.get(
                    self.LOGGED_IN_SEARCH,
                    params=params,
                    timeout=20,
                    allow_redirects=True,
                )
                if resp.status_code != 200:
                    continue

                for job in self._parse_search_html(resp.text):
                    jid = re.search(r"/jobs/view/(\d+)", job.url)
                    if jid and jid.group(1) not in seen_ids:
                        seen_ids.add(jid.group(1))
                        jobs.append(job)

                if len(jobs) >= 150:
                    break
            except Exception as e:
                print(f"  [LinkedIn] Logged-in search failed for '{kw}' in '{loc}': {e}")
        return jobs

    def _scrape_guest(self, search_pairs: List[Tuple[str, str]]) -> List[JobPost]:
        jobs = []
        seen_ids = set()
        for kw, loc in search_pairs:
            try:
                params = {
                    "keywords": kw,
                    "location": loc,
                    "f_WT": "2",
                    "f_TPR": "r86400",
                    "start": 0,
                }
                resp = self.session.get(self.GUEST_API, params=params, timeout=20)
                if resp.status_code != 200:
                    continue

                for job in self._parse_guest_html(resp.text):
                    jid = re.search(r"/jobs/view/(\d+)", job.url)
                    if jid and jid.group(1) not in seen_ids:
                        seen_ids.add(jid.group(1))
                        jobs.append(job)

                if len(jobs) >= 150:
                    break
            except Exception as e:
                print(f"  [LinkedIn] Guest search failed for '{kw}' in '{loc}': {e}")
        return jobs

    def _parse_search_html(self, html: str) -> List[JobPost]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        selectors = [
            "li.jobs-search-results__list-item",
            "div.job-card-container",
            "li[data-occludable-job-id]",
            "li[data-occ-billboard]",
        ]
        for card in soup.select(", ".join(selectors)):
            link = card.select_one("a[href*='/jobs/view/']")
            if not link:
                continue

            href = link.get("href", "").split("?")[0]
            title_el = card.select_one(
                "a[href*='/jobs/view/'] span[aria-hidden='true'], .job-card-list__title, h3"
            )
            company_el = card.select_one(
                ".job-card-container__company-name, .artdeco-entity-lockup__subtitle, span[data-anonymize='company-name']"
            )
            location_el = card.select_one(
                ".job-card-container__metadata-wrapper, .job-search-card__location, li[class*='location']"
            )
            time_el = card.select_one("time, .job-card-container__listed-state, .job-search-card__listdate")

            title = title_el.get_text(strip=True) if title_el else ""
            company = company_el.get_text(strip=True) if company_el else ""
            location = location_el.get_text(strip=True) if location_el else ""
            posted = self._parse_posted_date(time_el)

            if not title:
                continue
            if not href.startswith("http"):
                href = f"https://www.linkedin.com{href}"

            jobs.append(JobPost(
                title=title,
                company=company,
                location=location,
                description="",
                url=href,
                source=self.name,
                posted_date=posted,
                is_remote="remote" in location.lower(),
                apply_url=href,
                apply_button_active=False,
            ))
        return jobs

    def _parse_guest_html(self, html: str) -> List[JobPost]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for card in soup.select("li"):
            link = card.select_one("a.base-card__full-link")
            if not link:
                continue

            href = link.get("href", "")
            title_el = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle")
            location_el = card.select_one(".job-search-card__location")
            time_el = card.select_one("time.job-search-card__listdate")

            title = title_el.get_text(strip=True) if title_el else ""
            company = company_el.get_text(strip=True) if company_el else ""
            location = location_el.get_text(strip=True) if location_el else ""
            posted = self._parse_posted_date(time_el)

            if not title:
                continue
            if not href.startswith("http"):
                href = f"https://www.linkedin.com{href}"

            jobs.append(JobPost(
                title=title,
                company=company,
                location=location,
                description="",
                url=href,
                source=self.name,
                posted_date=posted,
                is_remote="remote" in location.lower(),
                apply_url=href,
                apply_button_active=False,
            ))
        return jobs

    def _parse_posted_date(self, time_el):
        if not time_el:
            return None

        raw_value = time_el.get("datetime") or time_el.get_text(strip=True)
        if not raw_value:
            return None

        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (AttributeError, TypeError, ValueError):
            return None

    def verify_job_active(self, url: str) -> bool:
        try:
            resp = self.session.get(url, timeout=15, allow_redirects=True)
            if resp.status_code != 200:
                return False

            text = resp.text.lower()
            if "this position has been filled" in text or "no longer accepting" in text:
                return False
            if "job search" in text and len(text) < 2000:
                return False
            return True
        except Exception:
            return False
