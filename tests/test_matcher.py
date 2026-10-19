from datetime import UTC, datetime, timedelta

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
        "posted_date": datetime.now(UTC) - timedelta(days=1),
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
        make_job(
            title="Frontend Developer React",
            description="React, TypeScript, JavaScript, HTML and CSS for web apps",
        ),
    ])
    assert len(accepted) == 2
    assert all(job.match_score >= matcher.min_score for job in accepted)


def test_spanish_bonus_capped_at_100():
    cv = load_cv()
    skills = [s for group in cv["core_skills"].values() for s in group]
    keywords = cv["company_fit_keywords"]
    matcher = JobMatcher()
    job = make_job(
        title="Junior QA Automation Engineer",
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


# --- Spec 004 ---------------------------------------------------------------

def test_score_scale_separates_good_and_generic():
    """RF-1 (spec 004): una oferta QA afín puntúa alto; una genérica no entra."""
    matcher = JobMatcher()
    good = make_job(
        title="QA Automation Engineer",
        description="Cypress, Playwright, JavaScript, TypeScript, Postman, CI/CD, E2E testing",
    )
    generic = make_job(title="Software Engineer", description="Golang, Kubernetes, Terraform, AWS")
    result = matcher.filter_jobs([good, generic])
    assert [j.title for j in result] == ["QA Automation Engineer"]
    assert result[0].match_score >= 80
    assert result[0].family == "qa"
    reasons = {r for _, _, r in matcher.last_excluded}
    assert reasons <= {"score_bajo", "rol_no_relacionado"}


def test_excluded_skill_penalizes_instead_of_zero():
    """RF-2 (spec 004): mencionar Selenium resta puntos pero no anula."""
    matcher = JobMatcher()
    job = make_job(description="Cypress, Playwright, JavaScript, TypeScript, Postman, Selenium")
    result = matcher.filter_jobs([job])
    assert len(result) == 1
    assert result[0].match_score < 100


def test_location_eligibility():
    """RF-3 (spec 004): fuera solo-EE. UU./España; dentro LATAM, Venezuela y genérico."""
    matcher = JobMatcher()
    desc = "Cypress, Playwright, JavaScript, TypeScript, Postman, CI/CD"
    jobs = [
        make_job(title="QA Engineer", location="United States", description=desc, url="u1"),
        make_job(title="QA Engineer", location="Madrid, Spain", description=desc, url="u2"),
        make_job(title="QA Engineer", location="Argentina, Brazil, United States, Venezuela", description=desc, url="u3"),
        make_job(title="QA Engineer", location="Remote", description=desc, url="u4"),
        make_job(title="QA Engineer", location="Bogotá, Colombia", description=desc, url="u5"),
        make_job(title="QA Engineer", location="Remote", description=desc + ". Candidates must reside in the US.", url="u6"),
    ]
    result = matcher.filter_jobs(jobs)
    assert sorted(j.url for j in result) == ["u3", "u4", "u5"]
    assert [r for _, _, r in matcher.last_excluded].count("ubicacion_no_elegible") == 3


def test_posting_language_filter():
    """RF-4 (spec 004): un aviso en alemán se excluye."""
    matcher = JobMatcher()
    job = make_job(
        title="Frontend Softwareentwickler (m/w/d)",
        description="Wir suchen einen Entwickler mit React und TypeScript für unser Team in der Cloud. "
                    "Du arbeitest mit uns an einer Plattform und bist für die Qualität der Software verantwortlich.",
        location="Remote",
    )
    assert matcher.filter_jobs([job]) == []
    assert matcher.last_excluded[0][2] == "idioma_publicacion"


def test_design_and_admin_families_are_relevant():
    """RF-9 (spec 004): diseño y administrativo entran como familias."""
    matcher = JobMatcher()
    design = make_job(title="UI/UX Designer", description="Figma, Photoshop, Illustrator, HTML, CSS, React", url="d")
    admin = make_job(title="Asistente Virtual Bilingüe", description="Google Workspace, data entry, Excel, CRM", url="a")
    fam_d = matcher.family_of(design)
    fam_a = matcher.family_of(admin)
    assert fam_d[0] == "design"
    assert fam_a[0] == "admin"
    result = matcher.filter_jobs([design])
    assert len(result) == 1
