import json
import os
from typing import List
from src.scrapers.base import JobPost

CV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "cvs", "profile.json")


def _load_cv() -> dict:
    try:
        with open(CV_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


class JobMatcher:
    def __init__(self):
        self.cv = _load_cv()
        self._build_indices()

    def _build_indices(self):
        cs = self.cv.get("core_skills", {})
        self.core_skills = []
        for group in cs.values():
            if isinstance(group, list):
                self.core_skills.extend(group)

        self.excluded_skills = [s.lower() for s in self.cv.get("skills_not_on_cv", {}).get("excluded", [])]

        self.job_titles = [t.lower() for t in self.cv.get("job_titles_fit", [])]
        self.exclude_titles = [t.lower() for t in self.cv.get("exclude_titles", [])]
        self.exclude_keywords = [t.lower() for t in self.cv.get("exclude_keywords_in_title", [])]

        lf = self.cv.get("location_filter", {})
        self.exclude_countries = {c.lower() for c in lf.get("exclude_countries", [])}
        self.exclude_regions = {r.lower() for r in lf.get("exclude_regions", [])}

        rf = self.cv.get("remote_type_filter", {})
        self.allowed_remote = {r.lower() for r in rf.get("allowed", [])}
        self.excluded_remote = {r.lower() for r in rf.get("excluded", [])}

        self.company_fit = [k.lower() for k in self.cv.get("company_fit_keywords", [])]

    def filter_jobs(self, jobs: List[JobPost]) -> List[JobPost]:
        filtered = []
        for job in jobs:
            if self._is_excluded(job):
                continue
            score = self._calculate_score(job)
            if score >= 20:
                job.match_score = round(score)
                filtered.append(job)
        filtered.sort(key=lambda j: j.match_score, reverse=True)
        return filtered

    def _is_excluded(self, job: JobPost) -> bool:
        if self._is_excluded_location(job):
            return True
        if self._is_excluded_title(job):
            return True
        if self._is_excluded_language(job):
            return True
        if not self._is_remote_ok(job):
            return True
        return False

    def _is_excluded_location(self, job: JobPost) -> bool:
        loc = job.location.lower()
        for country in self.exclude_countries:
            if country in loc:
                return True
        for region in self.exclude_regions:
            if region in loc:
                return True
        return False

    def _is_excluded_title(self, job: JobPost) -> bool:
        title = job.title.lower()
        for et in self.exclude_titles:
            if et in title:
                return True
        for ek in self.exclude_keywords:
            if ek in title:
                return True
        return False

    def _is_excluded_language(self, job: JobPost) -> bool:
        title = job.title.lower()
        desc = job.description.lower()
        combined = f"{title} {desc}"

        non_latin_scripts = ["汉", "日", "한", "العربية", "हिंदी", "русский", "ελληνικά"]
        for script in non_latin_scripts:
            if script in combined:
                return True

        east_asian_keywords = ["chinese", "japanese", "korean", "mandarin", "cantonese",
                               "mandarín", "japonés", "coreano", "cantonés"]
        for kw in east_asian_keywords:
            if kw in combined:
                return True

        return False

    def _is_remote_ok(self, job: JobPost) -> bool:
        if job.is_remote:
            return True

        loc = job.location.lower()
        for ar in self.allowed_remote:
            if ar in loc:
                return True

        for er in self.excluded_remote:
            if er in loc:
                return False

        title = job.title.lower()
        desc = job.description.lower()
        combined = f"{title} {desc} {loc}"

        remote_signals = ["remote", "remoto", "work from home", "wfh", "distributed",
                          "work from anywhere", "trabajo remoto", "fully remote"]
        for rs in remote_signals:
            if rs in combined:
                return True

        onsite_signals = ["on-site", "onsite", "in office", "office based", "presencial",
                          "hybrid", "hibrido", "híbrido", "en oficina"]
        for osig in onsite_signals:
            if osig in combined:
                return False

        return False

    def _calculate_score(self, job: JobPost) -> float:
        title = job.title.lower()
        desc = job.description.lower()
        combined = f"{title} {desc}"

        # Check for excluded skills first
        for es in self.excluded_skills:
            if es in combined:
                return 0

        score = 0

        # Title match (0-40)
        title_match = self._score_title_match(title)
        score += title_match

        # Skill match (0-40)
        skill_match = self._score_skill_match(combined)
        score += skill_match

        # Company fit (0-20)
        if self.company_fit:
            company_match = self._score_company_fit(combined)
            score += company_match

        return min(score, 100)

    def _score_title_match(self, title: str) -> float:
        for jt in self.job_titles:
            if jt in title:
                return 40

        partial_matches = [
            (["sdet"], 35),
            (["qa", "quality", "assurance", "test"], 25),
            (["automation", "automatiz"], 25),
            (["frontend", "front-end", "front end", "react"], 25),
            (["developer", "engineer", "desarrollador", "ingeniero"], 15),
            (["software"], 10),
            (["devops"], 20),
            (["full stack", "fullstack"], 15),
        ]
        for words, pts in partial_matches:
            if any(w in title for w in words):
                return pts
        return 0

    def _score_skill_match(self, combined_text: str) -> float:
        matched = 0
        total = max(len(self.core_skills), 1)
        for skill in self.core_skills:
            if skill.lower() in combined_text:
                matched += 1
        return min((matched / total) * 40, 40)

    def _score_company_fit(self, combined_text: float) -> float:
        matched = sum(1 for kw in self.company_fit if kw in combined_text)
        return min(matched * 3, 20)
