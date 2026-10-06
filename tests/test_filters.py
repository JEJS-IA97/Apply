from pathlib import Path

from src.analyzer.filters import LanguageFilter, LevelFilter, TrustFilter
from src.config import config
from src.profile import load_cv

CV = load_cv()


def test_level_filter_senior_titles():
    lf = LevelFilter(CV["level_filter"])
    assert lf.check_title("Senior QA Engineer") == "nivel_senior"
    assert lf.check_title("QA Lead") == "nivel_senior"
    assert lf.check_title("Staff Software Engineer") == "nivel_senior"
    assert lf.check_title("QA Automation Engineer II") == "nivel_senior"
    assert lf.check_title("QA Automation Engineer") is None
    assert lf.check_title("Junior QA Engineer") is None
    assert lf.check_title("") is None


def test_level_filter_years():
    lf = LevelFilter(CV["level_filter"])
    assert lf.check_experience("QA Engineer", "Requires 7+ years of experience") == "experiencia_excesiva"
    assert lf.check_experience("QA Engineer", "Minimum 5 years") == "experiencia_excesiva"
    assert lf.check_experience("QA Engineer", "3-5 years preferred") is None
    assert lf.check_experience("Junior QA Engineer", "5+ years required") is None


def test_trust_filter_blocked_company():
    tf = TrustFilter(CV["trust_filter"])
    assert tf.check("QA Engineer", "BairesDev", "") == "empresa_bloqueada"
    assert tf.check("QA Automation", "Baires Dev", "") == "empresa_bloqueada"
    assert tf.check("QA Automation", "Acme Corp", "great team") is None


def test_trust_filter_scam_signals():
    tf = TrustFilter(CV["trust_filter"])
    assert tf.check("Job", "Any", "Debes hacer un pago para aplicar") == "senal_scam"
    assert tf.check("Job", "Any", "solo whatsapp") == "senal_scam"
    assert tf.check("Job", "Any", "consigue empleo con ia hoy mismo") == "senal_scam"
    assert tf.check("QA Automation Engineer", "Acme", "Playwright and Cypress") is None


def test_language_filter_english_requirements():
    lf = LanguageFilter(CV["language_filter"])
    assert lf.check_english("QA Engineer", "Fluent English required") == "idioma_no_alcanzado"
    assert lf.check_english("Senior C1 English", "") == "idioma_no_alcanzado"
    assert lf.check_english("QA Engineer", "English B2 is fine") is None
    assert lf.check_english("QA Engineer", "Espanol o ingles") is None


def test_language_spanish_market_bonus_input():
    lf = LanguageFilter(CV["language_filter"])
    assert lf.is_spanish_market("QA", "remoto", "Colombia") is True
    assert lf.is_spanish_market("QA", "trabajo", "Espana") is False
    assert lf.is_spanish_market("QA", "remote", "United States") is False
    assert lf.is_spanish_market("QA", "remoto latam", "Remote") is True


def test_no_dead_filter_lists():
    """RF-10 (spec 001): ninguna lista de filtrado declarada sin consumidor."""
    assert not hasattr(config, "exclude_terms")
    assert not hasattr(config, "exclude_locations")

    consumed_keys = [
        "core_skills", "skills_not_on_cv", "job_titles_fit", "exclude_titles",
        "exclude_keywords_in_title", "location_filter", "remote_type_filter",
        "company_fit_keywords", "level_filter", "trust_filter",
        "language_filter", "relevance_filter", "platforms",
    ]
    sources = "\n".join(
        p.read_text(encoding="utf-8") for p in Path("src").rglob("*.py")
    )
    for key in consumed_keys:
        assert key in sources, f"lista sin consumidor en src/: {key}"
