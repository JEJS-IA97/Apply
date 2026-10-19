"""RF-10 (spec 004): exporta las ofertas filtradas para el front de GitHub Pages."""
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.scrapers.base import JobPost, normalize_url

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "docs" / "data" / "jobs.json"
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
APPLY_HINT = re.compile(
    r"(cv|resume|résumé|curr[ií]cul|hoja de vida|apply|postul|send|env[ií]a|aplica|hourly rate)", re.IGNORECASE
)
IGNORED_EMAIL = re.compile(r"(no-?reply|donotreply|privacy|example\.com|sentry|wixpress)", re.IGNORECASE)


def extract_apply_email(text: str) -> str | None:
    """Devuelve el correo de postulación si la oferta pide enviar el CV por email."""
    for match in EMAIL_RE.finditer(text or ""):
        email = match.group(0).rstrip(".")
        if IGNORED_EMAIL.search(email) or "x" * 4 in email:
            continue
        window = text[max(0, match.start() - 160): match.end() + 40]
        if APPLY_HINT.search(window):
            return email
    return None


def job_id(url: str) -> str:
    return hashlib.sha1(normalize_url(url).encode("utf-8")).hexdigest()[:12]


def to_record(job: JobPost, now: datetime) -> dict:
    email = job.apply_email or extract_apply_email(job.description)
    return {
        "id": job_id(job.url),
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "source": job.source,
        "family": job.family or "",
        "score": int(job.match_score or 0),
        "salary": job.salary or "",
        "url": job.apply_url or job.url,
        "apply_email": email or "",
        "posted": job.posted_date.date().isoformat() if job.posted_date else "",
        "found": now.date().isoformat(),
        "summary": re.sub(r"\s+", " ", job.description or "").strip()[:320],
        "curated": False,
    }


def export_jobs(jobs: list[JobPost], path: Path = DEFAULT_PATH, keep_days: int = 30,
                now: datetime | None = None) -> int:
    """Fusiona con el archivo existente: actualiza por id, conserva `curated`
    y elimina lo que tenga más de `keep_days` días desde que se encontró."""
    now = now or datetime.now(UTC)
    path = Path(path)
    existing: dict[str, dict] = {}
    if path.exists():
        try:
            for rec in json.loads(path.read_text(encoding="utf-8")).get("jobs", []):
                existing[rec["id"]] = rec
        except (ValueError, KeyError):
            existing = {}
    for job in jobs:
        rec = to_record(job, now)
        old = existing.get(rec["id"])
        if old:
            rec["found"] = old.get("found", rec["found"])
            rec["curated"] = old.get("curated", False)
            if rec["curated"]:
                # La nota escrita a mano vale más que el resumen automático.
                for field in ("summary", "fit", "note", "tags", "apply_email"):
                    if old.get(field):
                        rec[field] = old[field]
        existing[rec["id"]] = rec
    cutoff = (now - timedelta(days=keep_days)).date().isoformat()
    kept = [r for r in existing.values() if r.get("curated") or r.get("found", "") >= cutoff]
    kept.sort(key=lambda r: (r.get("score", 0), r.get("found", "")), reverse=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"updated": now.isoformat(timespec="minutes"), "jobs": kept}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return len(kept)
