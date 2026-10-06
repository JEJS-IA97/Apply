from datetime import datetime, timedelta, timezone

from src.analyzer.matcher import JobMatcher
from src.profile import load_cv
from src.scrapers.base import JobPost


def make_job(**kwargs):
    base = {
        "title": "QA Automation Engineer",
        "company": "Acme",
        "location": "Remote",
        "description": "Playwright and Cypress automation for web apps",
        "url": "https://example.com/job/1",
        "source": "Test",
        "is_remote": True,
        "posted_date": datetime.now(timezone.utc) - timedelta(days=1),
    }
    base.update(kwargs)
    return JobPost(**base)


def test_senior_titles_excluded_with_reason():
    matcher = JobMatcher()
    result = matcher.filter_jobs([make_job(title="Senior QA Automation Engineer")])
    assert result == []
    assert matcher.last_excluded[0][2] == "nivel_senior"


def test_excessive_experience_excluded():
    matcher = JobMatcher()
    result = matcher.filter_jobs(
        [make_job(description="Requires 7+ years of experience with test automation")]
    )
    assert result == []
    assert matcher.last_excluded[0][2] == "experiencia_excesiva"


def test_scam_signal_is_checked_before_level():
    matcher = JobMatcher()
    result = matcher.filter_jobs(
        [make_job(title="Senior QA Engineer", description="pago para aplicar")]
    )
    assert result == []
    assert matcher.last_excluded[0][2] == "senal_scam"


def test_blocked_company_excluded():
    matcher = JobMatcher()
    result = matcher.filter_jobs([make_job(company="BairesDev")])
    assert result == []
    assert matcher.last_excluded[0][2] == "empresa_bloqueada"


def test_role_relevance_gate():
    """RF-13 (spec 001): fuera Data Engineer/Compliance; dentro QA y Frontend."""
    matcher = JobMatcher()
    rejected = matcher.filter_jobs([
        make_job(title="Data Engineer, Data Quality"),
        make_job(title="Compliance Automation Analyst"),
    ])
    assert rejected == []
    reasons = {reason for _, _, reason in matcher.last_excluded}
    assert reasons == {"titulo_no_apto"}

    accepted = matcher.filter_jobs([
        make_job(title="QA Automation Engineer"),
        make_job(title="Frontend Developer React"),
    ])
    assert len(accepted) == 2
    assert all(job.match_score >= 20 for job in accepted)


def test_spanish_bonus_capped_at_100():
    cv = load_cv()
    skills = [s for group in cv["core_skills"].values() for s in group]
    keywords = cv["company_fit_keywords"]
    matcher = JobMatcher()
    job = make_job(
        location="Colombia",
        description=" ".join(skills + keywords),
    )
    result = matcher.filter_jobs([job])
    assert len(result) == 1
    assert result[0].match_score == 100


def test_post_jobs_pass_same_filters():
    """RF-7 (spec 002): las ofertas de tipo post atraviesan los mismos filtros."""
    matcher = JobMatcher()
    rejected = matcher.filter_jobs(
        [make_job(title="We are hiring a Senior Staff QA", post_source=True)]
    )
    assert rejected == []
    assert matcher.last_excluded[0][2] == "nivel_senior"

    cv = load_cv()
    all_skills = " ".join(s for group in cv["core_skills"].values() for s in group)
    accepted = matcher.filter_jobs([
        make_job(
            title="Hiring thread comment",
            description=f"We're hiring a QA Automation Engineer remote. Stack: {all_skills}",
            post_source=True,
        )
    ])
    assert len(accepted) == 1
    assert accepted[0].post_source is True
