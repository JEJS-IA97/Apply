"""RF-5 (spec 003): familias ATS con selectores registrados y validados.

Nunca se adivinan selectores: una familia solo es utilizable si sus
selectores fueron capturados de una pagina real (fixture en
tests/fixtures/) y no tiene bloqueo. La politica CAPTCHA aprobada
(2026-10-06): CAPTCHA interactivo visible bloquea la familia (RF-7);
tokens invisibles sin interaccion no son un desafio.
"""

from dataclasses import dataclass, field
from urllib.parse import urlparse

FIXTURE_DIR = "tests/fixtures"


@dataclass(frozen=True)
class FamilySpec:
    name: str
    host_patterns: tuple[str, ...]
    captcha: str  # "invisible" | "interactive" | "unknown"
    form_selector: str | None = None
    field_selectors: dict[str, str] = field(default_factory=dict)
    required_fields: tuple[str, ...] = ()
    submit_selector: str | None = None
    custom_question_selector: str | None = None
    fixture: str | None = None
    validated: bool = False
    blocked_reason: str | None = None

    @property
    def can_submit(self) -> bool:
        return self.validated and self.blocked_reason is None


FAMILIES: tuple[FamilySpec, ...] = (
    FamilySpec(
        name="greenhouse",
        host_patterns=("job-boards.greenhouse.io", "boards.greenhouse.io"),
        captcha="invisible",
        form_selector="#application-form",
        field_selectors={
            "first_name": "#first_name",
            "last_name": "#last_name",
            "email": "#email",
            "phone": "#phone",
            "location": "#candidate-location",
            "resume_file": "#resume",
            "cover_letter_file": "#cover_letter",
        },
        required_fields=("first_name", "last_name", "email", "phone", "location"),
        submit_selector="#application-form button[type='submit']",
        custom_question_selector="[id^='question_']",
        fixture=f"{FIXTURE_DIR}/ats_greenhouse.html",
        validated=True,
    ),
    FamilySpec(
        name="ashby",
        host_patterns=("jobs.ashbyhq.com",),
        captcha="interactive",
        field_selectors={
            "name": "#_systemfield_name",
            "email": "#_systemfield_email",
            "resume_file": "input[type='file'][accept*='pdf']",
        },
        required_fields=("name", "email"),
        submit_selector="button.ashby-application-form-submit-button",
        fixture=f"{FIXTURE_DIR}/ats_ashby_form.html",
        validated=True,
        blocked_reason="captcha_visible",
    ),
    FamilySpec(
        name="lever",
        host_patterns=("jobs.lever.co",),
        captcha="unknown",
        fixture=None,
        validated=False,
        blocked_reason="pendiente_captura",
    ),
    FamilySpec(
        name="workable",
        host_patterns=("apply.workable.com",),
        captcha="unknown",
        fixture=None,
        validated=False,
        blocked_reason="pendiente_captura",
    ),
)


def family_for(url: str) -> FamilySpec | None:
    """Devuelve la familia registrada para la URL o None (RF-5)."""
    if not url:
        return None
    host = urlparse(url if "//" in url else f"https://{url}").netloc.lower().removeprefix("www.")
    if not host:
        return None
    for family in FAMILIES:
        for pattern in family.host_patterns:
            if host == pattern or host.endswith(f".{pattern}"):
                return family
    return None


def submittable_family(url: str) -> FamilySpec | None:
    """Solo familias registradas, validadas y sin bloqueo (RF-5 + RF-7)."""
    family = family_for(url)
    if family is not None and family.can_submit:
        return family
    return None
