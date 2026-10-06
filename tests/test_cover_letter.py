from src.analyzer.cover_letter import CoverLetterGenerator
from src.profile import load_cv
from src.scrapers.base import JobPost


def _job(description):
    return JobPost(
        title="QA Automation Engineer",
        company="Acme Corp",
        location="Remote",
        description=description,
        url="https://example.com/job/1",
        source="Test",
    )


def test_skills_come_from_profile_json():
    """RF-11 (spec 001): la carta solo usa skills de cvs/profile.json."""
    cv = load_cv()
    json_skills = {s for group in cv["core_skills"].values() for s in group}
    default_only = {"Selenium", "Pytest", "Socket.io", "Python"}

    gen = CoverLetterGenerator()
    job = _job("Selenium Pytest Socket.io Python Cypress Playwright")

    matched = gen._extract_matched_skills(job)
    assert "Cypress" in matched
    assert "Playwright" in matched
    assert not (set(matched) & default_only)

    letter = gen.generate(job)
    assert "Selenium" not in letter
    assert "Pytest" not in letter
    assert "Socket.io" not in letter
    for skill in matched:
        assert skill in json_skills
