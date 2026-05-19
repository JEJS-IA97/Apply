from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import List, Optional


@dataclass
class JobPost:
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    posted_date: Optional[datetime] = None
    is_remote: bool = False
    apply_url: Optional[str] = None
    apply_button_active: bool = False
    salary: Optional[str] = None
    match_score: float = 0.0
    cover_letter: Optional[str] = None


class BaseScraper(ABC):
    TOKEN_EQUIVALENTS = (
        (r"\bfront-end\b", "front end"),
        (r"\bfrontend\b", "front end"),
        (r"\bfull-stack\b", "full stack"),
        (r"\bfullstack\b", "full stack"),
        (r"\bnode\.js\b", "node js"),
        (r"\bnodejs\b", "node js"),
        (r"\be2e\b", "end to end"),
        (r"\bqa\b", "quality assurance"),
    )
    SHORT_TOKENS = {"qa", "ui", "ux", "ai", "ml", "sdet", "api"}

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def scrape(self, keywords: List[str]) -> List[JobPost]:
        ...

    @abstractmethod
    def verify_job_active(self, url: str) -> bool:
        ...

    def is_recent(self, job: JobPost, max_days: int = 7) -> bool:
        if not job.posted_date:
            return True
        now = datetime.now(timezone.utc)
        posted = job.posted_date
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        delta = now - posted
        return delta.days <= max_days

    def normalize_text(self, text: str) -> str:
        normalized = (text or "").lower()
        for pattern, target in self.TOKEN_EQUIVALENTS:
            normalized = re.sub(pattern, target, normalized)
        normalized = re.sub(r"[^a-z0-9\s]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def unique_keywords(self, keywords: List[str]) -> List[str]:
        unique = []
        seen = set()
        for keyword in keywords:
            cleaned = " ".join((keyword or "").split())
            normalized = self.normalize_text(cleaned)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(cleaned)
        return unique

    def filter_keyword_jobs(self, jobs: List[JobPost], keywords: List[str]) -> List[JobPost]:
        if not keywords:
            return jobs
        return [job for job in jobs if self.matches_keywords(job, keywords)]

    def matches_keywords(self, job: JobPost, keywords: List[str]) -> bool:
        combined = self.normalize_text(
            f"{job.title} {job.company} {job.location} {job.description}"
        )
        if not combined:
            return False

        combined_tokens = set(combined.split())
        for keyword in self.unique_keywords(keywords):
            normalized = self.normalize_text(keyword)
            if normalized in combined:
                return True

            keyword_tokens = [
                token
                for token in normalized.split()
                if len(token) > 2 or token in self.SHORT_TOKENS
            ]
            if not keyword_tokens:
                continue

            overlap = sum(1 for token in keyword_tokens if token in combined_tokens)
            min_overlap = 1 if len(keyword_tokens) == 1 else 2
            if overlap >= min_overlap:
                return True

        return False
