import json
import os
import re

from src.analyzer.filters import LanguageFilter, LevelFilter, TrustFilter
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
        self.last_excluded: list[tuple[str, str, str]] = []
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

        self.level_filter = LevelFilter(self.cv.get("level_filter", {}))
        self.trust_filter = TrustFilter(self.cv.get("trust_filter", {}))
        self.language_filter = LanguageFilter(self.cv.get("language_filter", {}))

        rel = self.cv.get("relevance_filter", {})
        self.relevance_patterns = [re.compile(p, re.IGNORECASE) for p in rel.get("title_patterns", [])]
        self.min_score = float(rel.get("min_score", 20))

    def filter_jobs(self, jobs: list[JobPost]) -> list[JobPost]:
        filtered = []
        self.last_excluded = []
        for job in jobs:
            reason = self._exclusion_reason(job)
            if reason:
                self._reject(job, reason)
                continue
            if not self._is_relevant(job):
                self._reject(job, "rol_no_relacionado")
                continue
            score = self._calculate_score(job)
            if score < self.min_score:
                self._reject(job, "score_bajo")
                continue
            if self.language_filter.is_spanish_market(job.title, job.description, job.location):
                score = min(score + self.language_filter.spanish_bonus, 100)
            job.match_score = round(score)
            job.excluded_reason = None
            filtered.append(job)
        filtered.sort(key=lambda j: j.match_score, reverse=True)
        return filtered

    def _is_relevant(self, job: JobPost) -> bool:
        title = job.title.lower()
        if self._score_title_match(title) >= 40:
            return True
        text = title if not job.post_source else f"{title} {job.description.lower()}"
        return any(pattern.search(text) for pattern in self.relevance_patterns)

    def _reject(self, job: JobPost, reason: str) -> None:
        job.excluded_reason = reason
        self.last_excluded.append((job.source, job.title, reason))

    def _exclusion_reason(self, job: JobPost) -> str:
        trust = self.trust_filter.check(job.title, job.company, job.description)
        if trust:
            return trust

        english = self.language_filter.check_english(job.title, job.description)
        if english:
            return english
        if self._has_non_latin_script(job):
            return "idioma_no_latino"

        senior = self.level_filter.check_title(job.title)
        if senior:
            return senior
        years = self.level_filter.check_experience(job.title, job.description)
        if years:
            return years

        if self._is_excluded_title(job):
            return "titulo_no_apto"
        if self._is_excluded_location(job):
            return "ubicacion_no_apta"
        if not self._is_remote_ok(job):
            return "no_remoto"
        return ""

    def _has_non_latin_script(self, job: JobPost) -> bool:
        combined = f"{job.title} {job.description}".lower()
        non_latin_scripts = ["汉", "日", "한", "العربية", "हिंदी", "русский", "ελληνικά"]
        if any(script in combined for script in non_latin_scripts):
            return True
        east_asian_keywords = [
            "chinese", "japanese", "korean", "mandarin", "cantonese",
            "mandarín", "japonés", "coreano", "cantonés",
        ]
        return any(kw in combined for kw in east_asian_keywords)

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

        remote_signals = [
            "remote", "remoto", "work from home", "wfh", "distributed",
            "work from anywhere", "trabajo remoto", "fully remote",
        ]
        if any(rs in combined for rs in remote_signals):
            return True

        onsite_signals = [
            "on-site", "onsite", "in office", "office based", "presencial",
            "hybrid", "hibrido", "híbrido", "en oficina",
        ]
        for osig in onsite_signals:
            if osig in combined:
                return False
        return False

    def _calculate_score(self, job: JobPost) -> float:
        title = job.title.lower()
        desc = job.description.lower()
        combined = f"{title} {desc}"

        for es in self.excluded_skills:
            if es in combined:
                return 0

        score = self._score_title_match(title)
        score += self._score_skill_match(combined)
        if self.company_fit:
            score += self._score_company_fit(combined)

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

    def _score_company_fit(self, combined_text: str) -> float:
        matched = sum(1 for kw in self.company_fit if kw in combined_text)
        return min(matched * 3, 20)
