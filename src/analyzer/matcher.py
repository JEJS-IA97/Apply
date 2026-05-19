import re
from typing import List
from src.config import config
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
        self.profile_skills = self._unique_terms(profile.skills)
        self.target_roles = self._unique_terms(
            config.search_keywords + [part.strip() for part in profile.title.split("/") if part.strip()]
        )

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
        loc = self._normalize(job.location)
        return any(ex in loc for ex in self.excluded_locations)

    def _is_excluded_title(self, job: JobPost) -> bool:
        title = self._normalize(job.title)
        if "hybrid" in title or "on-site" in title or "onsite" in title:
            return True
        return False

    def _is_remote(self, job: JobPost) -> bool:
        if job.is_remote:
            return True
        text = self._normalize(f"{job.title} {job.description} {job.location}")
        if "remote" in text or "remoto" in text:
            return True
        if "hybrid" in text or "on-site" in text or "presencial" in text:
            return False
        return False

    def _calculate_match(self, job: JobPost) -> float:
        title = self._normalize(job.title)
        combined = self._normalize(f"{job.title} {job.description} {job.company} {job.location}")

        matched_profile_skills = sum(1 for skill in self.profile_skills if skill in combined)
        matched_broad_skills = sum(1 for skill in BROAD_SKILLS if self._normalize(skill) in combined)
        skill_score = min(1.0, ((matched_profile_skills * 1.5) + (matched_broad_skills * 0.5)) / 18.0)

        title_bonus = 0.0
        for role in self.target_roles:
            if role in title:
                title_bonus = 0.3
                break

        return skill_score * 0.7 + title_bonus

    def _normalize(self, text: str) -> str:
        normalized = (text or "").lower()
        replacements = (
            (r"\bfront-end\b", "front end"),
            (r"\bfrontend\b", "front end"),
            (r"\bfull-stack\b", "full stack"),
            (r"\bfullstack\b", "full stack"),
            (r"\bnode\.js\b", "node js"),
            (r"\bnodejs\b", "node js"),
            (r"\be2e\b", "end to end"),
            (r"\bqa\b", "quality assurance"),
        )
        for pattern, target in replacements:
            normalized = re.sub(pattern, target, normalized)
        normalized = re.sub(r"[^a-z0-9\s]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def _unique_terms(self, values: List[str]) -> List[str]:
        unique = []
        seen = set()
        for value in values:
            normalized = self._normalize(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(normalized)
        return unique
