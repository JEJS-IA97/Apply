from typing import List
from src.scrapers.base import JobPost
from src.profile import profile


BROAD_SKILLS = [
    "qa", "quality assurance", "automation", "test", "testing", "sdet",
    "frontend", "front-end", "front end", "react", "full stack", "fullstack",
    "javascript", "typescript", "python", "node", "nodejs", "node.js",
    "html", "css", "api", "rest", "e2e", "integration testing",
    "cypress", "playwright", "selenium", "postman", "appium", "pytest",
    "cucumber", "git", "ci/cd", "ci", "cd", "azure", "mongodb",
    "mysql", "postgresql", "sql", "database", "unit test",
    "agile", "scrum", "devops", "cloud", "docker", "kubernetes",
    "ui", "ux", "responsive", "mobile", "web", "software",
    "developer", "engineer", "development", "engineering"
]


class JobMatcher:
    def __init__(self):
        self.excluded_locations = {
            "india", "asia", "bangalore", "mumbai", "hyderabad",
            "chennai", "pune", "delhi", "kolkata", "ahmedabad",
            "noida", "gurgaon", "philippines", "pakistan",
            "bangladesh", "sri lanka", "vietnam", "indonesia",
            "thailand", "malaysia", "china", "singapore",
            "kuala lumpur", "manila", "jakarta", "dhaka",
            "colombo", "hanoi", "ho chi minh", "bangkok"
        }

    def filter_jobs(self, jobs: List[JobPost]) -> List[JobPost]:
        filtered = []
        for job in jobs:
            reasons = []
            if self._is_excluded_location(job):
                reasons.append(f"loc:{job.location}")
            if self._is_excluded_title(job):
                reasons.append("title_excl")
            if not self._is_remote(job):
                reasons.append("not_remote")
            if reasons:
                print(f"    FILTERED: [{job.source}] {job.title[:50]} @ {job.company[:20]} => {', '.join(reasons)}")
                continue
            score = self._calculate_match(job)
            if score < 0.05:
                print(f"    LOW SCORE: [{job.source}] {job.title[:50]} @ {job.company[:20]} => score={score:.3f}")
                continue
            job.match_score = round(score, 2)
            filtered.append(job)
        filtered.sort(key=lambda j: j.match_score, reverse=True)
        return filtered

    def _is_excluded_location(self, job: JobPost) -> bool:
        loc = job.location.lower().strip()
        return any(ex in loc for ex in self.excluded_locations)

    def _is_excluded_title(self, job: JobPost) -> bool:
        title = job.title.lower()
        if "hybrid" in title or "on-site" in title or "onsite" in title:
            return True
        return False

    def _is_remote(self, job: JobPost) -> bool:
        if job.is_remote:
            return True
        text = f"{job.title.lower()} {job.description.lower()} {job.location.lower()}"
        if "remote" in text or "remoto" in text:
            return True
        if "hybrid" in text or "on-site" in text or "presencial" in text:
            return False
        return False

    def _calculate_match(self, job: JobPost) -> float:
        title = job.title.lower()
        desc = job.description.lower()
        combined = f"{title} {desc}"

        matched = sum(1 for s in BROAD_SKILLS if s in combined)
        skill_score = matched / 40.0

        title_bonus = 0.0
        target_roles = [
            "qa", "quality assurance", "automation", "test", "sdet",
            "frontend", "front-end", "front end", "react", "full stack",
            "fullstack", "developer", "engineer", "software"
        ]
        for role in target_roles:
            if role in title:
                title_bonus = 0.3
                break

        return skill_score * 0.7 + title_bonus
