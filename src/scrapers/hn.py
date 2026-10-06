import html
import re
from datetime import datetime, timedelta, timezone

from src.scrapers.base import BaseScraper, JobPost

API = "https://hn.algolia.com/api/v1"
UA = {"User-Agent": "ApplyJobBot/1.0 (contact: jose.e.jimenez.1411@gmail.com)"}
MAX_TEXT = 1500


def _strip_html(text: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or ""))).strip()


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class HackerNewsScraper(BaseScraper):
    """Hacker News vía API pública de Algolia (RF-2, spec 002):
    tablero oficial de empleos `tags=job`, publicaciones de contratación
    (`tags=story`) y comentarios del hilo mensual "Who is hiring?"."""

    trusts_freshness = True
    max_requests = 6

    def __init__(self):
        super().__init__("HackerNews")

    def scrape(self, keywords: list[str]) -> list[JobPost]:
        jobs: list[JobPost] = []
        jobs.extend(self._scrape_job_board())
        jobs.extend(self._scrape_hiring_thread())
        return self.filter_keyword_jobs(jobs, keywords)

    def _get(self, params: dict) -> list[dict]:
        resp = self.request(f"{API}/search_by_date", params=params, headers=UA, timeout=20)
        if resp is None or resp.status_code != 200:
            return []
        try:
            return resp.json().get("hits", [])
        except ValueError:
            return []

    def _scrape_job_board(self) -> list[JobPost]:
        since = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
        hits = self._get({
            "tags": "job",
            "hitsPerPage": 50,
            "numericFilters": f"created_at_i>{since}",
        })
        jobs = []
        for hit in hits:
            title = _strip_html(hit.get("title") or "")
            if not title:
                continue
            company = ""
            match = re.match(r"^(.+?)\s+is hiring", title, re.IGNORECASE)
            if match and "who is hiring" not in title.lower():
                company = match.group(1).strip()
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
            jobs.append(JobPost(
                title=title, company=company, location="Remote",
                description=title, url=url, source=self.name,
                posted_date=_parse_timestamp(hit.get("created_at", "")),
                is_remote=True, apply_url=url, apply_button_active=True,
                post_source=True,
            ))
        return jobs

    def _scrape_hiring_thread(self) -> list[JobPost]:
        stories = self._get({"query": "who is hiring", "tags": "story", "hitsPerPage": 1})
        if not stories:
            return []
        story = stories[0]
        story_id = story.get("objectID")
        if not story_id:
            return []
        since = int((datetime.now(timezone.utc) - timedelta(days=45)).timestamp())
        comments = self._get({
            "tags": "comment",
            "numericFilters": f"story_id={story_id},created_at_i>{since}",
            "hitsPerPage": 40,
        })
        jobs = []
        for comment in comments:
            job = self._parse_comment(comment)
            if job:
                jobs.append(job)
        return jobs

    def _parse_comment(self, hit: dict) -> JobPost | None:
        text = _strip_html(hit.get("comment_text") or "")
        if len(text) < 60:
            return None
        lowered = text.lower()
        company, title, location = self._split_pipe_format(text)
        if not title:
            title = text[:140]
        url = f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
        return JobPost(
            title=title, company=company, location=location or "Remote",
            description=text[:MAX_TEXT], url=url, source=self.name,
            posted_date=_parse_timestamp(hit.get("created_at", "")),
            is_remote="remote" in lowered or "anywhere" in lowered,
            apply_url=url, apply_button_active=True,
            post_source=True,
        )

    @staticmethod
    def _split_pipe_format(text: str) -> tuple:
        head = text[:200]
        if "|" not in head:
            return "", "", ""
        parts = [p.strip() for p in head.split("|") if p.strip()]
        if len(parts) < 2:
            return "", "", ""
        company = parts[0][:80]
        title = parts[1][:140] if len(parts[1]) > 3 else ""
        location = parts[2][:80] if len(parts) > 2 else ""
        return company, title, location

    def verify_job_active(self, url: str) -> bool:
        return True
