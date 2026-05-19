import re
import requests
from datetime import datetime, timezone
from typing import List, Optional
from bs4 import BeautifulSoup
from src.scrapers.base import BaseScraper, JobPost

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


class LinkedInScraper(BaseScraper):
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
                allow_redirects=True
            )
            self.logged_in = "li_at" in self.session.cookies or "login" not in resp2.url.lower()
            if self.logged_in:
                print("  [LinkedIn] Logged in successfully")
            else:
                print("  [LinkedIn] Login failed (may need CAPTCHA)")
        except Exception as e:
            print(f"  [LinkedIn] Login error: {e}")

    SEARCH_TERMS = [
        ("QA Automation", "Latin America"),
        ("QA Engineer", "Latin America"),
        ("QA Analyst", "Latin America"),
        ("Quality Assurance", "Latin America"),
        ("Automation Engineer", "Latin America"),
        ("Frontend Developer", "Latin America"),
        ("React Developer", "Latin America"),
        ("SDET", "Latin America"),
        ("QA Automation", "Mexico"),
        ("QA Engineer", "Mexico"),
        ("QA Automation", "Colombia"),
        ("QA Engineer", "Colombia"),
        ("QA Automation", "Argentina"),
        ("QA Engineer", "Argentina"),
        ("QA Automation", "Chile"),
        ("QA Engineer", "Chile"),
        ("QA Automation", "Peru"),
        ("QA Engineer", "Peru"),
        ("QA Automation", "Costa Rica"),
        ("QA Engineer", "Costa Rica"),
        ("Analista de calidad", "América Latina"),
        ("Aseguramiento de calidad", "América Latina"),
        ("QA Automation", "Venezuela"),
        ("QA Engineer", "Venezuela"),
        ("Quality Assurance", "Venezuela"),
        ("QA Tester", "Latin America"),
        ("QA Analyst", "Mexico"),
        ("QA Analyst", "Colombia"),
        ("QA Analyst", "Argentina"),
    ]

    GUEST_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        return self._search_jobs()

    def _search_jobs(self) -> List[JobPost]:
        jobs = []
        seen_ids = set()
        terms = self.SEARCH_TERMS
        for kw, loc in terms:
            try:
                params = {
                    "keywords": kw,
                    "location": loc,
                    "f_WT": "2",
                    "f_TPR": "r86400",
                    "start": 0,
                }
                resp = self.session.get(
                    self.GUEST_API,
                    params=params,
                    timeout=20
                )
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for card in soup.select("li"):
                    link = card.select_one("a.base-card__full-link")
                    if not link:
                        continue
                    href = link.get("href", "")
                    jid = re.search(r'/jobs/view/(\d+)', href)
                    if not jid or jid.group(1) in seen_ids:
                        continue
                    seen_ids.add(jid.group(1))
                    title_el = card.select_one("h3.base-search-card__title")
                    company_el = card.select_one("h4.base-search-card__subtitle")
                    location_el = card.select_one(".job-search-card__location")
                    time_el = card.select_one("time.job-search-card__listdate")
                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = location_el.get_text(strip=True) if location_el else ""
                    if not title:
                        continue
                    if not href.startswith("http"):
                        href = f"https://www.linkedin.com{href}"
                    jobs.append(JobPost(
                        title=title, company=company, location=location,
                        description="", url=href, source=self.name,
                        is_remote="remote" in location.lower(),
                        apply_url=href, apply_button_active=False
                    ))
                if len(jobs) >= 100:
                    break
            except Exception:
                continue
        return jobs



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
