import json
from datetime import UTC, datetime, timedelta

from src.exporter import export_jobs, extract_apply_email
from src.scrapers.base import JobPost


def _job(url, score=80, desc=""):
    job = JobPost(title="QA Engineer", company="Acme", location="Remote", description=desc,
                  url=url, source="Torre", is_remote=True)
    job.match_score = score
    job.family = "qa"
    return job


def test_extract_apply_email():
    """RF-10 (spec 004): detecta postulación por correo."""
    assert extract_apply_email("Envía tu CV y hourly rate en USD a corip.work@gmail.com") == "corip.work@gmail.com"
    assert extract_apply_email("Contact noreply@company.com for support") is None
    assert extract_apply_email("Our office email is hello@acme.com") is None


def test_export_merges_and_expires(tmp_path):
    path = tmp_path / "jobs.json"
    now = datetime(2026, 10, 19, tzinfo=UTC)
    old = now - timedelta(days=40)
    export_jobs([_job("https://a.com/1")], path, now=old)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["jobs"].append({"id": "manual", "title": "Curada", "found": "2026-01-01", "curated": True, "score": 90})
    path.write_text(json.dumps(data), encoding="utf-8")

    total = export_jobs([_job("https://b.com/2", desc="Send your CV to jobs@acme.io")], path, now=now)
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = [r["id"] for r in data["jobs"]]
    assert total == 2
    assert "manual" in ids
    assert data["jobs"][-1]["apply_email"] == "jobs@acme.io" or data["jobs"][0]["apply_email"] == "jobs@acme.io"


def test_export_keeps_curated_notes(tmp_path):
    """RF-10 (spec 004): si el bot reencuentra una oferta curada, no pisa la nota escrita a mano."""
    from src.exporter import job_id
    path = tmp_path / "jobs.json"
    url = "https://a.com/1"
    path.write_text(json.dumps({"jobs": [{"id": job_id(url), "title": "QA", "found": "2026-10-01", "curated": True,
                                          "summary": "Nota a mano", "fit": "encaja", "score": 70}]}), encoding="utf-8")
    export_jobs([_job(url, score=88, desc="texto del scraper")], path, now=datetime(2026, 10, 19, tzinfo=UTC))
    rec = json.loads(path.read_text(encoding="utf-8"))["jobs"][0]
    assert rec["summary"] == "Nota a mano" and rec["fit"] == "encaja"
    assert rec["score"] == 88 and rec["found"] == "2026-10-01"
