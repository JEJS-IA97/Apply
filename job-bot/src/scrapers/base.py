from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
        delta = datetime.now(timezone.utc) - job.posted_date
        return delta.days <= max_days
