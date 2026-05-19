import re
from typing import List, Set
from src.scrapers.base import JobPost
from src.profile import profile


class JobMatcher:
    def __init__(self):
        self.skill_keywords = {s.lower() for s in profile.skills}
        self.exclude_locations = {loc.lower().strip() for loc in [
            "india", "asia", "bangalore", "mumbai", "hyderabad",
            "chennai", "pune", "delhi", "kolkata", "ahmedabad",
            "noida", "gurgaon", "philippines", "pakistan",
            "bangladesh", "sri lanka", "vietnam", "indonesia",
            "thailand", "malaysia", "china", "singapore",
            "kuala lumpur", "manila", "jakarta", "dhaka",
            "colombo", "hanoi", "ho chi minh", "bangkok"
        ]}
        self.exclude_terms = {"hybrid", "on-site", "onsite", "senior staff", "principal"}

    def filter_jobs(self, jobs: List[JobPost]) -> List[JobPost]:
        filtered = []
        for job in jobs:
            if self._is_excluded_location(job):
                continue
            if self._is_excluded_term(job):
                continue
            if not self._is_remote(job):
                continue
            score = self._calculate_match(job)
            if score >= 0.15:
                job.match_score = round(score, 2)
                filtered.append(job)
        filtered.sort(key=lambda j: j.match_score, reverse=True)
        return filtered

    def _is_excluded_location(self, job: JobPost) -> bool:
        loc = job.location.lower().strip()
        if any(ex in loc for ex in self.exclude_locations):
            return True
        full_text = f"{job.title.lower()} {job.description.lower()}"
        if any(ex in full_text for ex in self.exclude_locations):
            return True
        return False

    def _is_excluded_term(self, job: JobPost) -> bool:
        text = f"{job.title.lower()} {job.description.lower()}"
        return any(term in text for term in self.exclude_terms)

    def _is_remote(self, job: JobPost) -> bool:
        if job.is_remote:
            return True
        text = f"{job.title.lower()} {job.description.lower()} {job.location.lower()}"
        if "remote" in text or "100% remoto" in text or "trabajo remoto" in text:
            return True
        if "hybrid" in text or "on-site" in text or "presencial" in text:
            return False
        return False

    def _calculate_match(self, job: JobPost) -> float:
        text = f"{job.title.lower()} {job.description.lower()}"
        title_text = job.title.lower()
        matched_skills = 0
        for skill in self.skill_keywords:
            if skill in text:
                matched_skills += 1
        skill_ratio = matched_skills / max(len(self.skill_keywords), 1)
        title_bonus = 0.0
        target_roles = [
            "qa", "quality assurance", "automation", "test", "sdet",
            "frontend", "front-end", "front end", "react", "full stack"
        ]
        for role in target_roles:
            if role in title_text:
                title_bonus = 0.3
                break
        return skill_ratio * 0.7 + title_bonus
