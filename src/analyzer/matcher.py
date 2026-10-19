import json
import os
import re
from typing import ClassVar

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

        self.families = []
        self.family_skills: dict[str, list[str]] = {}
        for name, fam in (self.cv.get("job_families") or {}).items():
            if isinstance(fam, dict) and fam.get("patterns"):
                self.families.append((
                    name,
                    float(fam.get("points", 0)),
                    [re.compile(p, re.IGNORECASE) for p in fam["patterns"]],
                ))
                if fam.get("skills"):
                    self.family_skills[name] = list(fam["skills"])

        self.allowed_location_terms = [t.lower() for t in lf.get("allowed_terms", [])]
        self.allowed_countries = [c.lower() for c in lf.get("allowed_countries", [])]
        self.blocked_locations = [b.lower() for b in lf.get("blocked_locations", [])]
        self.residency_patterns = [re.compile(p, re.IGNORECASE) for p in lf.get("residency_patterns", [])]
        self.rejected_post_langs = set((self.cv.get("posting_language_filter") or {}).get("rejected", []))
        self.excluded_skill_patterns = [
            re.compile(r"(?<![a-z0-9])" + re.escape(s) + r"(?![a-z0-9])") for s in self.excluded_skills
        ]

        rel = self.cv.get("relevance_filter", {})
        self.relevance_patterns = [re.compile(p, re.IGNORECASE) for p in rel.get("title_patterns", [])]
        self.min_score = float(rel.get("min_score", 55))
        self.report_limit = int(rel.get("report_limit", 20))

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
        if not self._is_eligible_location(job):
            return "ubicacion_no_elegible"
        if self._posting_language(job) in self.rejected_post_langs:
            return "idioma_publicacion"
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

    _FOREIGN_STOPWORDS: ClassVar[dict[str, set[str]]] = {
        "de": {"und", "der", "die", "das", "mit", "für", "wir", "sie", "ist", "eine", "oder", "auf", "bei", "deine", "ihre"},
        "pt": {"você", "não", "vaga", "para", "com", "uma", "nossa", "requisitos", "experiência", "conhecimento", "trabalho", "são", "também", "desenvolvimento"},
        "fr": {"nous", "vous", "avec", "pour", "est", "une", "dans", "les", "des", "votre", "poste", "être", "notre", "équipe"},
    }
    _BASE_STOPWORDS: ClassVar[dict[str, set[str]]] = {
        "es": {"el", "la", "los", "las", "con", "para", "una", "que", "experiencia", "conocimiento", "trabajo", "nuestro", "somos", "buscamos"},
        "en": {"the", "and", "with", "you", "our", "for", "are", "will", "experience", "team", "your", "we"},
    }

    def _posting_language(self, job: JobPost) -> str:
        """RF-4 (spec 004): idioma dominante del aviso por palabras vacías."""
        words = re.findall(r"[a-záéíóúâêôãõçàèùäöüßñ]+", f"{job.title} {job.description}".lower())
        if len(words) < 8:
            return ""
        counts = {}
        for lang, stop in {**self._FOREIGN_STOPWORDS, **self._BASE_STOPWORDS}.items():
            counts[lang] = sum(1 for w in words if w in stop)
        best = max(counts, key=counts.get)
        if best in self._FOREIGN_STOPWORDS and counts[best] >= 4:
            base = max(counts["es"], counts["en"])
            if counts[best] > base:
                return best
        return ""

    def _is_eligible_location(self, job: JobPost) -> bool:
        """RF-3 (spec 004): elegible si nombra un país/término permitido,
        no elegible si solo nombra lugares bloqueados o si la descripción
        exige residir en un país no permitido."""
        desc = (job.description or "").lower()
        if any(p.search(desc) for p in self.residency_patterns):
            return False
        loc = (job.location or "").lower()
        if not loc:
            return True
        if any(t in loc for t in self.allowed_location_terms):
            return True
        if any(re.search(r"(?<![a-z])" + re.escape(c) + r"(?![a-z])", loc) for c in self.allowed_countries):
            return True
        return not any(re.search(r"(?<![a-z])" + re.escape(b) + r"(?![a-z])", loc) for b in self.blocked_locations)

    def family_of(self, job: JobPost) -> tuple[str, float]:
        """RF-1/RF-9 (spec 004): familia del título con más puntos."""
        text = job.title if not job.post_source else f"{job.title} {job.description}"
        best = ("", 0.0)
        for name, points, patterns in self.families:
            if points > best[1] and any(p.search(text) for p in patterns):
                best = (name, points)
        if not best[0]:
            title = job.title.lower()
            for jt in self.job_titles:
                if jt in title:
                    return ("generic", 15.0)
        return best

    def _calculate_score(self, job: JobPost) -> float:
        """RF-1 y RF-2 (spec 004): escala 0-100 con sentido."""
        title = job.title.lower()
        desc = (job.description or "").lower()
        combined = f"{title} {desc}"

        family, score = self.family_of(job)
        job.family = family or None

        score += self._score_skill_match(combined, self.family_skills.get(family, []))
        if self.language_filter.is_spanish_market(job.title, job.description, job.location):
            score += min(self.language_filter.spanish_bonus * 2, 10)
        if any(re.search(r"(?<![a-z])" + re.escape(m) + r"(?![a-z])", title) for m in self.level_filter.allowed_markers):
            score += 5
        if self.company_fit:
            score += self._score_company_fit(combined)

        penalties = sum(1 for p in self.excluded_skill_patterns if p.search(combined))
        score -= min(penalties * 4, 16)
        return max(0, min(score, 100))

    def _score_title_match(self, title: str) -> float:
        """Compatibilidad: puntos de familia para un título suelto."""
        return self.family_of(JobPost(title=title, company="", location="", description="", url="", source=""))[1]

    def _score_skill_match(self, combined_text: str, extra: list[str] | None = None) -> float:
        matched = 0
        for skill in dict.fromkeys(self.core_skills + list(extra or [])):
            if re.search(r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])", combined_text):
                matched += 1
        return min(matched, 6) / 6 * 35

    def _score_company_fit(self, combined_text: str) -> float:
        matched = sum(1 for kw in self.company_fit if kw in combined_text)
        return min(matched * 2, 5)
