"""Fase 2, T2 (spec 003): flujo de postulación por oferta.

Flujo (plan.md, fase 2): resolver URL → familia registrada → rellenar
solo con datos de ``cvs/profile.json`` → enviar → confirmar → evidencia.
RF-3 (envío con evidencia), RF-6 (fallo limpio, un solo intento),
RF-5 (gate de familia), RF-7 (familias con CAPTCHA visible nunca llegan
aquí: ``submittable_family``), RNF-1 (90 s por envío).
RF-10 se garantiza en la integración (T5): el runner solo se invoca
después de los filtros de las specs 001/002. P6: nunca se inventan
datos; un campo obligatorio sin dato en el perfil es ``dato_faltante``.
"""

import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin

import requests

from src.apply.registry import FamilySpec, family_for, submittable_family
from src.scrapers.base import JobPost

SUBMIT_TIMEOUT_MS = 90_000  # RNF-1
UA = {"User-Agent": "ApplyJobBot/1.0 (contact: jose.e.jimenez.1411@gmail.com)"}
HREF_RE = re.compile(r'href="([^"]+)"')

INTERACTIVE_CAPTCHA_SELECTORS = (
    "iframe[title='reCAPTCHA']",
    "iframe[src*='hcaptcha.com']",
    "#challenge-form",
    "iframe[src*='challenges.cloudflare.com']",
)
LOGIN_URL_MARKERS = (
    "/login",
    "/signin",
    "/sign-in",
    "/account/login",
    "/session/new",
    "/auth/login",
    "/auth/signin",
)


def detect_block(page) -> str | None:
    """RF-7 (decisión 2026-10-06): detecta CAPTCHA interactivo visible o
    control de acceso en la página. Tokens invisibles (iframe oculto o
    badge) no cuentan: no son un desafío que resolver."""
    url = (getattr(page, "url", "") or "").lower()
    if "captcha" in url:
        return "captcha"
    if any(marker in url for marker in LOGIN_URL_MARKERS):
        return "login"
    for selector in INTERACTIVE_CAPTCHA_SELECTORS:
        locator = page.locator(selector).first
        if locator.count() and locator.is_visible():
            return "captcha"
    return None


@dataclass
class FormPlan:
    values: dict[str, str] = field(default_factory=dict)
    files: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)


@dataclass
class ApplyResult:
    outcome: str  # enviado | dominio_no_soportado | dato_faltante | error
    family: str | None = None
    detail: str | None = None
    confirmation_url: str | None = None
    evidence: str | None = None


def _split_name(full: str) -> tuple[str, str]:
    parts = (full or "").split(None, 1)
    if not parts:
        return "", ""
    return parts[0], (parts[1] if len(parts) > 1 else "")


def build_form_plan(family: FamilySpec, profile: dict) -> FormPlan:
    """Rellena solo con datos existentes en el perfil (P6)."""
    plan = FormPlan()
    name = (profile.get("name") or "").strip()
    first, last = _split_name(name)
    sources = {
        "name": name,
        "first_name": first,
        "last_name": last,
        "email": (profile.get("email") or "").strip(),
        "phone": (profile.get("phone") or "").strip(),
        "location": (profile.get("location") or "").strip(),
        "linkedin": (profile.get("linkedin") or "").strip(),
        "github": (profile.get("github") or "").strip(),
    }
    for field_key in family.required_fields:
        selector = family.field_selectors.get(field_key)
        value = sources.get(field_key, "")
        if not selector or not value:
            plan.missing.append(field_key)
        else:
            plan.values[selector] = value
    for field_key, selector in family.field_selectors.items():
        if field_key in plan.missing or selector in plan.values:
            continue
        if field_key in ("resume_file", "cover_letter_file"):
            continue
        value = sources.get(field_key, "")
        if value:
            plan.values[selector] = value
    cv_file = (profile.get("cv_file") or "").strip()
    resume_selector = family.field_selectors.get("resume_file")
    if cv_file and resume_selector:
        plan.files[resume_selector] = cv_file
    return plan


def _default_fetch(url: str) -> tuple[str, str]:
    resp = requests.get(url, headers=UA, timeout=12, allow_redirects=True)
    body = resp.text if resp.status_code == 200 else ""
    return resp.url, body


def resolve_ats_url(url: str, fetch=None) -> str:
    """Paso 1 del flujo: redirecciones de la oferta y enlaces salientes
    hasta caer en una familia ATS registrada. Devuelve la URL resuelta
    (o la original si no hay familia)."""
    if family_for(url):
        return url
    fetch = fetch or _default_fetch
    try:
        final_url, body = fetch(url)
    except requests.RequestException:
        return url
    if family_for(final_url):
        return final_url
    source = final_url or url
    for match in HREF_RE.finditer(body[:500_000]):
        candidate = urljoin(source, match.group(1))
        if family_for(candidate):
            return candidate
    return source


def fill_form(page, family: FamilySpec, plan: FormPlan) -> None:
    for selector, value in plan.values.items():
        page.fill(selector, value)
    for selector, path in plan.files.items():
        page.set_input_files(selector, path)


def run_application(
    job: JobPost,
    profile: dict,
    page,
    *,
    resolver=resolve_ats_url,
    ats_url: str | None = None,
    status=None,
    now=time.monotonic,
) -> ApplyResult:
    """Un solo intento por oferta (RF-6), con tope de 90 s (RNF-1).

    ``ats_url`` permite pasar la URL ya resuelta por el llamador (lote,
    T3) para no repetir la petición de resolución. ``status`` (T4) es el
    registro de mantenimiento de familias: si un selector no aparece,
    la familia queda ``validated: false`` y deja de recibir envíos.
    """
    raw_url = (job.apply_url or "").strip()
    if not raw_url:
        return ApplyResult(outcome="dominio_no_soportado", detail="sin_apply_url")
    if ats_url is None:
        ats_url = resolver(raw_url)
    family = submittable_family(ats_url)
    if family is None:
        registered = family_for(ats_url)
        detail = "sin_selectores_validados" if registered else "dominio_no_registrado"
        if registered is not None and not registered.can_submit:
            detail = registered.blocked_reason or "bloqueada"
        return ApplyResult(outcome="dominio_no_soportado", detail=detail)
    if status is not None and not status.is_active(family.name):
        return ApplyResult(
            outcome="dominio_no_soportado",
            family=family.name,
            detail="requiere_mantenimiento",
        )
    plan = build_form_plan(family, profile)
    if plan.missing:
        return ApplyResult(
            outcome="dato_faltante",
            family=family.name,
            detail=",".join(plan.missing),
        )
    deadline = now() + SUBMIT_TIMEOUT_MS / 1000

    def remaining_ms() -> int:
        left = int((deadline - now()) * 1000)
        if left <= 0:
            raise TimeoutError("timeout_90s")
        return left

    def blocked() -> ApplyResult | None:
        kind = detect_block(page)
        if kind:
            return ApplyResult(outcome="bloqueo", family=family.name, detail=kind)
        return None

    def selector_failure(detail: str) -> ApplyResult:
        if status is not None:
            status.demote(family.name, "selector_ausente")
        return ApplyResult(outcome="error", family=family.name, detail=detail)

    try:
        page.goto(ats_url, timeout=remaining_ms())
        hit = blocked()
        if hit:
            return hit
        wait_selector = family.form_selector or next(iter(family.field_selectors.values()))
        try:
            page.wait_for_selector(wait_selector, timeout=remaining_ms())
        except Exception as exc:
            if "timeout_90s" in str(exc):
                raise
            return selector_failure("selector_ausente")
        hit = blocked()
        if hit:
            return hit
        if family.custom_question_selector:
            custom_required = page.locator(
                f"{family.custom_question_selector}[aria-required='true'], "
                f"{family.custom_question_selector}[required]"
            ).count()
            if custom_required:
                return ApplyResult(
                    outcome="dato_faltante",
                    family=family.name,
                    detail="custom_questions",
                )
        if not family.submit_selector:
            return ApplyResult(
                outcome="error",
                family=family.name,
                detail="sin_selector_submit",
            )
        required = [*plan.values, *plan.files, family.submit_selector]
        absent = [sel for sel in required if page.locator(sel).first.count() == 0]
        if absent:
            return selector_failure(f"selector_ausente:{absent[0]}")
        form_url = page.url
        fill_form(page, family, plan)
        page.click(family.submit_selector)
        page.wait_for_url(
            lambda candidate: (candidate or "").rstrip("/") != form_url.rstrip("/"),
            timeout=remaining_ms(),
        )
        hit = blocked()
        if hit:
            return hit
    except Exception as exc:  # noqa: BLE001
        detail = str(exc) or type(exc).__name__
        if not isinstance(exc, TimeoutError) and now() >= deadline:
            detail = "timeout_90s"
        return ApplyResult(outcome="error", family=family.name, detail=detail)
    return ApplyResult(
        outcome="enviado",
        family=family.name,
        confirmation_url=page.url,
        evidence=page.content(),
    )
