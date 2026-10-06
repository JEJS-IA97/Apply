import importlib.util
import re
from datetime import datetime

from src.profile import load_cv
from src.scrapers.base import BaseScraper, JobPost

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
SEARCH_URL = "https://www.linkedin.com/search/results/content/?keywords={query}&origin=GLOBAL_SEARCH_HEADER"
LOGIN_URL = "https://www.linkedin.com/login"
RESTRICTION_MARKERS = (
    "security verification", "verify your identity", "challenge",
    "unusual activity", "captcha", "too many attempts", "suspended",
)
JOB_MARKERS = ("hiring", "we're hiring", "we are hiring", "estamos buscando",
               "estamos contratando", "vacante", "job opening", "referral")


def playwright_available() -> bool:
    return importlib.util.find_spec("playwright") is not None


class LinkedInPostsScraper(BaseScraper):
    """Publicaciones de LinkedIn con hashtags/términos de contratación
    (RF-11, spec 002). Requiere credenciales propias + Playwright.

    Si LinkedIn muestra CAPTCHA o una señal de restricción, la fuente se
    detiene para la ejecución y queda registrada: no se elude ningún control."""

    max_requests = 12
    trusts_freshness = True

    def __init__(self, email: str, password: str):
        super().__init__("LinkedInPosts")
        self.email = email
        self.password = password
        self.blocked_reason = ""
        self.queries = self._queries()

    def _queries(self) -> list[str]:
        platforms = load_cv().get("platforms", {})
        terms = platforms.get("post_search_terms", [])[:6]
        hashtags = platforms.get("post_hashtags", [])[:4]
        return [f"{t} {h}".strip() for t in terms for h in hashtags[:1]] or ["hiring"]

    def scrape(self, keywords: list[str]) -> list[JobPost]:
        if self.blocked_reason:
            print(f"  [LinkedInPosts] DETENIDA: {self.blocked_reason}")
            return []
        if not playwright_available():
            self.blocked_reason = "playwright no instalado"
            print(f"  [LinkedInPosts] {self.blocked_reason}")
            return []
        try:
            return self.filter_keyword_jobs(self._scrape_with_browser(), keywords)
        except Exception as e:  # noqa: BLE001
            self.blocked_reason = f"error de navegador: {e}"
            print(f"  [LinkedInPosts] {self.blocked_reason}")
            return []

    def _scrape_with_browser(self) -> list[JobPost]:
        from playwright.sync_api import sync_playwright

        jobs: list[JobPost] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=UA, locale="en-US")
            page = context.new_page()
            try:
                if not self._login(page):
                    self.blocked_reason = "login fallido"
                    return []
                for query in self.queries:
                    if self.blocked_reason or self.requests_made >= self.max_requests:
                        break
                    page.goto(SEARCH_URL.format(query=query.replace(" ", "%20")), timeout=30000)
                    page.wait_for_timeout(2500)
                    html = page.content()
                    if self._is_restricted(html):
                        self.blocked_reason = "LinkedIn pidió verificación/captcha"
                        jobs = []
                        break
                    jobs.extend(self.extract_posts(html))
            finally:
                browser.close()
        return jobs

    def _login(self, page) -> bool:
        page.goto(LOGIN_URL, timeout=30000)
        page.fill("#username", self.email)
        page.fill("#password", self.password)
        page.click("button[type='submit']")
        page.wait_for_timeout(4000)
        if page.url.startswith(LOGIN_URL) or page.locator("#password").count() > 0:
            return False
        return not self._is_restricted(page.content())

    @staticmethod
    def _is_restricted(html: str) -> bool:
        lowered = (html or "").lower()
        return any(marker in lowered for marker in RESTRICTION_MARKERS)

    @staticmethod
    def extract_posts(html: str) -> list[JobPost]:
        """Parser puro (probado con fixture): extrae publicaciones con oferta."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html or "", "html.parser")
        jobs = []
        for block in soup.select(".feed-shared-update-v2, div[data-urn^='urn:li:activity']"):
            text_el = block.select_one(".feed-shared-text, .update-components-text, span.feed-shared-text__text")
            text = re.sub(r"\s+", " ", (text_el.get_text(" ", strip=True) if text_el else "")).strip()
            if len(text) < 40:
                continue
            lowered = text.lower()
            if not any(marker in lowered for marker in JOB_MARKERS):
                continue
            link = block.select_one("a[href*='/posts/'], a[href*='/feedUpdate/']")
            url = link.get("href", "").split("?")[0] if link else ""
            if not url:
                continue
            time_el = block.select_one("time")
            posted = None
            if time_el and time_el.get("datetime"):
                try:
                    posted = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
                except ValueError:
                    posted = None
            jobs.append(JobPost(
                title=text[:140], company="", location="",
                description=text[:1500], url=url, source="LinkedInPosts",
                posted_date=posted, is_remote=("remote" in lowered or "remoto" in lowered),
                apply_url=url, apply_button_active=True, post_source=True,
            ))
        return jobs

    def verify_job_active(self, url: str) -> bool:
        return True
