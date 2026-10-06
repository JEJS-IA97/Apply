import html
import re
from datetime import datetime

from src.profile import load_cv
from src.scrapers.base import BaseScraper, JobPost

UA = {"User-Agent": "ApplyJobBot/1.0 (contact: jose.e.jimenez.1411@gmail.com)"}
MAX_TEXT = 1500
MAX_TITLE = 140


def _strip_html(text: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or ""))).strip()


class MastodonScraper(BaseScraper):
    """Hashtags de contratación en timelines públicos de Mastodon (RF-4, spec 002).

    Sin credenciales: solo endpoints públicos de instancias configuradas en
    `cvs/profile.json -> platforms.mastodon_instances`."""

    trusts_freshness = True
    max_requests = 30

    def __init__(self, instances: list[str] | None = None, hashtags: list[str] | None = None,
                 search_terms: list[str] | None = None):
        super().__init__("Mastodon")
        cv = load_cv().get("platforms", {})
        self.instances = instances if instances is not None else cv.get("mastodon_instances", [])
        self.hashtags = hashtags if hashtags is not None else cv.get("post_hashtags", [])
        self.search_terms = [t.lower() for t in (
            search_terms if search_terms is not None else cv.get("post_search_terms", [])
        )]

    def scrape(self, keywords: list[str]) -> list[JobPost]:
        jobs: list[JobPost] = []
        for instance in self.instances:
            for hashtag in self.hashtags:
                job_list = self._fetch_tag(instance, hashtag)
                jobs.extend(job_list)
                if self.requests_made >= self.max_requests:
                    return self.filter_keyword_jobs(jobs, keywords)
        return self.filter_keyword_jobs(jobs, keywords)

    def _fetch_tag(self, instance: str, hashtag: str) -> list[JobPost]:
        tag = hashtag.lstrip("#")
        url = f"https://{instance}/api/v1/timelines/tag/{tag}"
        resp = self.request(url, params={"limit": 20}, headers=UA, timeout=20)
        if resp is None or resp.status_code != 200:
            return []
        try:
            statuses = resp.json()
        except ValueError:
            return []
        jobs = []
        for status in statuses:
            job = self._parse_status(status, instance)
            if job:
                jobs.append(job)
        return jobs

    def _parse_status(self, status: dict, instance: str) -> JobPost | None:
        text = _strip_html(status.get("content") or "")
        if len(text) < 40:
            return None
        lowered = text.lower()
        if self.search_terms and not any(term in lowered for term in self.search_terms):
            return None
        url = status.get("url") or status.get("uri") or ""
        if not url:
            return None
        created = status.get("created_at")
        posted = None
        if created:
            try:
                posted = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                posted = None
        is_remote = any(s in lowered for s in ("remote", "remoto", "desde casa", "work from home"))
        return JobPost(
            title=text[:MAX_TITLE],
            company="",
            location="Remote" if is_remote else instance,
            description=text[:MAX_TEXT],
            url=url,
            source=self.name,
            posted_date=posted,
            is_remote=is_remote,
            apply_url=url,
            apply_button_active=True,
            post_source=True,
        )

    def verify_job_active(self, url: str) -> bool:
        return True
