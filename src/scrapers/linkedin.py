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

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        if self.logged_in:
            return self._scrape_logged_in(keywords)
        return self._scrape_guest(keywords)

    def _scrape_logged_in(self, keywords: List[str]) -> List[JobPost]:
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
                    "https://www.linkedin.com/jobs/search/",
                    params=params,
                    timeout=20,
                    allow_redirects=True
                )
                if resp.status_code != 200:
                    continue
                jobs.extend(self._parse_search_html(resp.text, kw))
            except Exception:
                continue
        return jobs

    def _scrape_guest(self, keywords: List[str]) -> List[JobPost]:
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
                    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                    params=params,
                    timeout=20
                )
                if resp.status_code != 200:
                    continue
                jobs.extend(self._parse_guest_html(resp.text))
            except Exception:
                continue
        return jobs

    def _parse_search_html(self, html: str, keyword: str) -> List[JobPost]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for card in soup.select("li.jobs-search-results__list-item, div.job-card-container, li[data-occ-billboard]"):
            link = card.select_one("a[href*='/jobs/view/']")
            if not link:
                continue
            href = link.get("href", "").split("?")[0]
            title_el = card.select_one("a[href*='/jobs/view/'] span, .job-card-list__title, h3")
            company_el = card.select_one(".job-card-container__company-name, .artdeco-entity-lockup__subtitle, span[data-anonymize=company-name]")
            location_el = card.select_one(".job-card-container__metadata-wrapper, .job-search-card__location, li[class*='location']")
            time_el = card.select_one("time, .job-card-container__listed-state, .job-search-card__listdate")
            title = title_el.get_text(strip=True) if title_el else ""
            company = company_el.get_text(strip=True) if company_el else ""
            location = location_el.get_text(strip=True) if location_el else ""
            posted = None
            if time_el:
                dt = time_el.get("datetime") or time_el.get_text(strip=True)
                if dt:
                    try:
                        parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=timezone.utc)
                        posted = parsed
                    except (ValueError, TypeError):
                        posted = None
            if title:
                if not href.startswith("http"):
                    href = f"https://www.linkedin.com{href}"
                jobs.append(JobPost(
                    title=title, company=company, location=location,
                    description="", url=href, source=self.name,
                    posted_date=posted, is_remote="remote" in location.lower(),
                    apply_url=href, apply_button_active=False
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
            posted = None
            if time_el and time_el.get("datetime"):
                try:
                    posted = datetime.fromisoformat(time_el["datetime"])
                except ValueError:
                    pass
            if title:
                if not href.startswith("http"):
                    href = f"https://www.linkedin.com{href}"
                jobs.append(JobPost(
                    title=title, company=company, location=location,
                    description="", url=href, source=self.name,
                    posted_date=posted, is_remote="remote" in location.lower(),
                    apply_url=href, apply_button_active=False
                ))
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
