from datetime import datetime
from typing import List, Optional
from src.scrapers.base import BaseScraper, JobPost


class RedditScraper(BaseScraper):
    def __init__(self, client_id: str = "", client_secret: str = "", user_agent: str = "job-bot/1.0"):
        super().__init__("Reddit")
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self._praw = None

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

    def scrape(self, keywords: List[str]) -> List[JobPost]:
        if not self.praw:
            return self.filter_keyword_jobs(self._scrape_without_auth(), keywords)
        return self.filter_keyword_jobs(self._scrape_with_auth(), keywords)

    def _scrape_without_auth(self) -> List[JobPost]:
        import requests
        jobs = []
        subreddits = ["remotejs", "forhire", "jobbit", "remotejobs", "freelance"]
        for sub in subreddits:
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
            except Exception:
                continue
        return jobs

    def _scrape_with_auth(self) -> List[JobPost]:
        jobs = []
        subreddits = ["remotejs", "forhire", "jobbit", "remotejobs", "freelance", "QualityAssurance"]
        for sub in subreddits:
            try:
                for post in self.praw.subreddit(sub).new(limit=50):
                    job = self._parse_praw_post(post, sub)
                    if job:
                        jobs.append(job)
            except Exception:
                continue
        return jobs

    def _parse_reddit_post(self, data: dict, sub: str) -> Optional[JobPost]:
        title = data.get("title", "")
        selftext = data.get("selftext", "")
        url = f"https://www.reddit.com{data.get('permalink', '')}"
        created = datetime.utcfromtimestamp(data.get("created_utc", 0)) if data.get("created_utc") else None
        return JobPost(
            title=title, company=f"r/{sub}", location="Remote",
            description=selftext[:2000], url=url, source=self.name,
            posted_date=created, is_remote=True,
            apply_url=url, apply_button_active=True
        )

    def _parse_praw_post(self, post, sub: str) -> Optional[JobPost]:
        import praw
        title = post.title
        selftext = post.selftext[:2000] if post.selftext else ""
        url = f"https://www.reddit.com{post.permalink}"
        created = datetime.utcfromtimestamp(post.created_utc) if post.created_utc else None
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
        except Exception:
            return False
