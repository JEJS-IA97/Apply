from datetime import datetime, timezone

from src.profile import load_cv
from src.scrapers.base import BaseScraper, JobPost

DEFAULT_SUBREDDITS = ["remotejs", "forhire", "jobbit", "remotejobs", "freelance"]
DEFAULT_SEARCH_TERMS = ["flair:hiring", "hiring qa"]


class RedditScraper(BaseScraper):
    """Foros de Reddit (RF-5, spec 002). El gate de credenciales vive en
    `registry.py`: sin REDDIT_CLIENT_ID/SECRET la fuente queda `disabled`
    con causa (la API pública responde 403), no un vacío silencioso."""

    def __init__(self, client_id: str = "", client_secret: str = "", user_agent: str = "job-bot/1.0"):
        super().__init__("Reddit")
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self._praw = None
        platforms = load_cv().get("platforms", {})
        self.subreddits = platforms.get("reddit_subreddits") or DEFAULT_SUBREDDITS
        self.search_terms = platforms.get("reddit_search_terms") or DEFAULT_SEARCH_TERMS

    @property
    def praw(self):
        if self._praw is None and self.client_id and self.client_secret:
            import praw
            self._praw = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
        return self._praw

    def scrape(self, keywords: list[str]) -> list[JobPost]:
        if not self.praw:
            return self.filter_keyword_jobs(self._scrape_without_auth(), keywords)
        return self.filter_keyword_jobs(self._scrape_with_auth(), keywords)

    def _scrape_without_auth(self) -> list[JobPost]:
        import requests
        jobs = []
        for sub in self.subreddits[:5]:
            try:
                resp = requests.get(
                    f"https://www.reddit.com/r/{sub}/new.json",
                    params={"limit": 50},
                    headers={"User-Agent": self.user_agent},
                    timeout=15
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for post in data.get("data", {}).get("children", []):
                    job = self._parse_reddit_post(post.get("data", {}), sub)
                    if job:
                        jobs.append(job)
            except Exception:  # noqa: BLE001, S112
                continue
        return jobs

    def _scrape_with_auth(self) -> list[JobPost]:
        jobs = []
        seen = set()
        joined = "+".join(self.subreddits[:6])
        try:
            for post in self.praw.subreddit(joined).new(limit=50):
                job = self._parse_praw_post(post, post.subreddit.display_name)
                if job and job.url not in seen:
                    seen.add(job.url)
                    jobs.append(job)
        except Exception as e:  # noqa: BLE001
            print(f"  [Reddit] new(): {e}")
        for term in self.search_terms[:4]:
            try:
                for post in self.praw.subreddit(joined).search(term, sort="new", time_filter="week", limit=20):
                    job = self._parse_praw_post(post, post.subreddit.display_name)
                    if job and job.url not in seen:
                        seen.add(job.url)
                        jobs.append(job)
            except Exception as e:  # noqa: BLE001
                print(f"  [Reddit] search({term!r}): {e}")
        return jobs

    def _parse_reddit_post(self, data: dict, sub: str) -> JobPost | None:
        title = data.get("title", "")
        selftext = data.get("selftext", "")
        url = f"https://www.reddit.com{data.get('permalink', '')}"
        created = datetime.fromtimestamp(data.get("created_utc", 0), tz=timezone.utc) if data.get("created_utc") else None
        return JobPost(
            title=title, company=f"r/{sub}", location="Remote",
            description=selftext[:2000], url=url, source=self.name,
            posted_date=created, is_remote=True,
            apply_url=url, apply_button_active=True
        )

    def _parse_praw_post(self, post, sub: str) -> JobPost | None:
        title = post.title
        selftext = post.selftext[:2000] if post.selftext else ""
        url = f"https://www.reddit.com{post.permalink}"
        created = datetime.fromtimestamp(post.created_utc, tz=timezone.utc) if post.created_utc else None
        return JobPost(
            title=title, company=f"r/{sub}", location="Remote",
            description=selftext, url=url, source=self.name,
            posted_date=created, is_remote=True,
            apply_url=url, apply_button_active=True
        )

    def verify_job_active(self, url: str) -> bool:
        try:
            import requests
            resp = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=10)
            return resp.status_code == 200
        except Exception:  # noqa: BLE001
            return False
