"""RF-7 (spec 004): bolsa pública de Torre para trabajo remoto desde Venezuela.

Listado: https://torre.ai/sub/<subtorre>/jobs/<página> (HTML con enlaces /post/<id>-<slug>).
Detalle: https://torre.ai/api/suite/opportunities/<id> (JSON público).
"""
import re
from datetime import datetime

import requests

from src.profile import load_cv
from src.scrapers.base import BaseScraper, JobPost

BASE = "https://torre.ai"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
POST_RE = re.compile(r"/post/([A-Za-z0-9]{8})-([a-z0-9-]+)")
SLUG_EXCLUDE = re.compile(r"(?:^|-)(senior|sr|lead|head|director|manager|principal|chief)(?:-|$)")


def _strip(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


class TorreScraper(BaseScraper):
    trusts_freshness = True
    max_requests = 30
    pages = 8

    def __init__(self, subtorre: str = ""):
        super().__init__("Torre")
        self.subtorre = subtorre or load_cv().get("platforms", {}).get("torre_subtorre", "trabajo-remoto-venezuela")

    def scrape(self, keywords: list[str]) -> list[JobPost]:
        slugs: dict[str, str] = {}
        for page in range(1, self.pages + 1):
            try:
                resp = self.request(f"{BASE}/sub/{self.subtorre}/jobs/{page}", headers={"User-Agent": UA}, timeout=20)
            except requests.RequestException:
                break
            if resp is None or resp.status_code != 200:
                break
            found = POST_RE.findall(resp.text)
            if not found:
                break
            for opp_id, slug in found:
                slugs.setdefault(opp_id, slug)

        candidates = [
            (opp_id, slug) for opp_id, slug in slugs.items()
            if not SLUG_EXCLUDE.search(slug) and self._slug_matches(slug, keywords)
        ]
        jobs = []
        for opp_id, slug in candidates:
            try:
                resp = self.request(f"{BASE}/api/suite/opportunities/{opp_id}", headers={"User-Agent": UA}, timeout=20)
            except requests.RequestException:
                break
            if resp is None:
                break
            if resp.status_code != 200:
                continue
            try:
                job = self.parse_opportunity(resp.json(), slug)
            except ValueError:
                continue
            if job:
                jobs.append(job)
        return jobs

    def _slug_matches(self, slug: str, keywords: list[str]) -> bool:
        text = slug.replace("-", " ")
        return any(
            all(tok in text for tok in self.normalize_text(kw).split() if len(tok) > 2 or tok in self.SHORT_TOKENS)
            for kw in self.unique_keywords(keywords)
        ) or bool(re.search(r"\b(qa|tester|testing|quality|frontend|front end|react|ux|ui|designer|disenador|graphic|assistant|asistente|data entry)\b", text))

    @staticmethod
    def parse_opportunity(data: dict, slug: str = "") -> JobPost | None:
        if data.get("status") not in (None, "open"):
            return None
        title = data.get("objective") or ""
        if not title:
            return None
        orgs = data.get("organizations") or []
        company = orgs[0].get("name", "") if orgs else ""
        place = data.get("place") or {}
        if place.get("anywhere"):
            location = "Remote (Worldwide)"
        elif place.get("timezone"):
            tzs = data.get("timezones") or []
            location = "Remote (LATAM time zones " + ", ".join(tzs) + ")" if tzs else "Remote"
        else:
            location = "Remote" if place.get("remote") else ""

        langs = []
        for lang in data.get("languages") or []:
            name = (lang.get("language") or {}).get("name", "")
            fluency = (lang.get("fluency") or "").replace("fully-fluent", "fluent")
            if name:
                langs.append(f"{name}: {fluency}")
        details = " ".join(_strip(d.get("content", "")) for d in data.get("details") or [])
        strengths = ", ".join(s.get("name", "") for s in data.get("strengths") or [])
        description = " ".join(filter(None, [details, f"Skills: {strengths}" if strengths else "", "Languages: " + "; ".join(langs) if langs else ""]))

        comp = data.get("compensation") or {}
        comp = comp.get("data", comp) if isinstance(comp, dict) else {}
        salary = None
        if comp.get("minAmount") or comp.get("maxAmount"):
            salary = f"{comp.get('minAmount') or ''}-{comp.get('maxAmount') or ''} {comp.get('currency', '')}/{comp.get('periodicity', '')}".strip()

        posted = None
        if data.get("created"):
            try:
                posted = datetime.fromisoformat(data["created"])
            except ValueError:
                posted = None
        url = f"{BASE}/post/{data.get('id')}-{slug}" if slug else f"{BASE}/post/{data.get('id')}"
        return JobPost(
            title=title, company=company, location=location, description=description,
            url=url, source="Torre", posted_date=posted, is_remote=bool(place.get("remote", True)),
            apply_url=url, salary=salary,
        )

    def verify_job_active(self, url: str) -> bool:
        return True
