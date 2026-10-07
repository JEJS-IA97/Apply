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


def test_gemini_used_when_key_set(monkeypatch):
    """RF-14: con GEMINI_API_KEY la carta sale del modelo Gemini."""
    captured = {}

    def fake_post(url, params=None, json=None, timeout=None):
        captured["url"] = url
        captured["key"] = params["key"]
        captured["body"] = json
        captured["timeout"] = timeout

        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "candidates": [
                        {"content": {"parts": [{"text": "  MODEL LETTER  "}]}}
                    ]
                }

        return Resp()

    monkeypatch.setattr("src.analyzer.cover_letter.requests.post", fake_post)
    gen = CoverLetterGenerator(gemini_api_key="TEST-KEY", model="gemini-test")
    letter = gen.generate(_job("Cypress Playwright"))
    assert letter == "MODEL LETTER"
    assert "gemini-test:generateContent" in captured["url"]
    assert captured["key"] == "TEST-KEY"
    assert "contents" in captured["body"]
    assert captured["timeout"] == 30


def test_gemini_error_falls_back_to_template(monkeypatch):
    """RF-14: fallo de red/API -> plantilla, sin interrumpir."""

    def fake_post(*args, **kwargs):
        raise RuntimeError("api down")

    monkeypatch.setattr("src.analyzer.cover_letter.requests.post", fake_post)
    letter = CoverLetterGenerator(gemini_api_key="TEST-KEY").generate(_job("Cypress"))
    assert "Dear Hiring Manager" in letter


def test_gemini_empty_response_falls_back(monkeypatch):
    """RF-14: respuesta sin candidatos -> plantilla."""

    def fake_post(*args, **kwargs):
        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"candidates": []}

        return Resp()

    monkeypatch.setattr("src.analyzer.cover_letter.requests.post", fake_post)
    letter = CoverLetterGenerator(gemini_api_key="K").generate(_job("Cypress"))
    assert "Dear Hiring Manager" in letter


def test_no_key_uses_template():
    """Sin clave: plantilla (modo por defecto)."""
    letter = CoverLetterGenerator().generate(_job("Cypress"))
    assert "Dear Hiring Manager" in letter


def test_config_exposes_gemini_not_openai():
    """RF-14: config con GEMINI_* y sin openai_api_key."""
    from src.config import config

    assert hasattr(config, "gemini_api_key")
    assert hasattr(config, "gemini_model")
    assert not hasattr(config, "openai_api_key")
