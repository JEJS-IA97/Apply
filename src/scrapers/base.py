import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import ClassVar
from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """URL canónica para deduplicación (RF-8, spec 002): sin fragmentos ni
    parámetros de tracking (utm_*, ref, position, trk...)."""
    if not url:
        return ""
    try:
        parts = urlparse(url.strip())
    except ValueError:
        return url.strip()
    query_pairs = [
        pair for pair in parts.query.split("&")
        if pair and not pair.lower().startswith(("utm_", "ref", "trk", "position", "tracking"))
    ]
    path = parts.path.rstrip("/")
    return urlunparse((parts.scheme.lower(), parts.netloc.lower(), path, "", "&".join(query_pairs), ""))


@dataclass
class JobPost:
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    posted_date: datetime | None = None
    is_remote: bool = False
    apply_url: str | None = None
    apply_button_active: bool = False
    salary: str | None = None
    match_score: float = 0.0
    cover_letter: str | None = None
    excluded_reason: str | None = None
    post_source: bool = False


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
    SHORT_TOKENS: ClassVar[set] = {"qa", "ui", "ux", "ai", "ml", "sdet", "api"}

    trusts_freshness: bool = False
    max_requests: int = 30
    disabled_reason: str = ""

    def __init__(self, name: str):
        self.name = name
        self.requests_made = 0

    @abstractmethod
    def scrape(self, keywords: list[str]) -> list[JobPost]:
        ...

    @abstractmethod
    def verify_job_active(self, url: str) -> bool:
        ...

    def request(self, url: str, **kwargs):
        """Petición HTTP con presupuesto por fuente y por ejecución (RF-9, spec 002).
        Devuelve None cuando la fuente agotó su presupuesto."""
        if self.requests_made >= self.max_requests:
            return None
        import requests
        self.requests_made += 1
        return requests.get(url, **kwargs)

    def enrich(self, job: JobPost) -> bool | None:
        """Completación opcional de la oferta (p.ej. descripción) usando como
        mucho una petición. Devuelve False si la oferta ya no existe."""
        return None

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

    def unique_keywords(self, keywords: list[str]) -> list[str]:
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

    def filter_keyword_jobs(self, jobs: list[JobPost], keywords: list[str]) -> list[JobPost]:
        """Pre-gate de keywords para fuentes de feed de empleos.

        Decisión 6 de specs/002 plan.md (aprobada 2026-10-06): los posts y
        comentarios (`post_source=True`) no se prefiltran aquí; decide el
        gate de relevancia del matcher (RF-13 spec 001).
        """
        if not keywords:
            return jobs
        return [
            job
            for job in jobs
            if job.post_source or self.matches_keywords(job, keywords)
        ]

    def matches_keywords(self, job: JobPost, keywords: list[str]) -> bool:
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
