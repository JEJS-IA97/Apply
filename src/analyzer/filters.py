import re


def _contains_marker(text: str, marker: str) -> bool:
    if not text or not marker:
        return False
    return re.search(r"(?<!\w)" + re.escape(marker) + r"(?!\w)", text) is not None


class LevelFilter:
    """RF-1, RF-2 y RF-3 (spec 001): nivel senior/experiencia exigida."""

    def __init__(self, cfg: dict):
        self.excluded_markers: list[str] = [m.lower() for m in cfg.get("excluded_title_markers", [])]
        self.excluded_patterns: list[str] = list(cfg.get("excluded_title_patterns", []))
        self.allowed_markers: list[str] = [m.lower() for m in cfg.get("allowed_title_markers", [])]
        self.min_years: int = int(cfg.get("min_years_excluded", 5))
        self.years_patterns: list[str] = list(
            cfg.get("years_patterns", [r"(\d+)\s*(?:-\s*\d+)?\s*\+?\s*(?:years|años|yrs|yr)"])
        )

    def check_title(self, title: str) -> str | None:
        t = (title or "").lower()
        if not t:
            return None
        for marker in self.excluded_markers:
            if _contains_marker(t, marker):
                return "nivel_senior"
        for pattern in self.excluded_patterns:
            if re.search(pattern, t):
                return "nivel_senior"
        return None

    def check_experience(self, title: str, description: str) -> str | None:
        t = (title or "").lower()
        if any(_contains_marker(t, m) for m in self.allowed_markers):
            return None
        text = f"{t} {(description or '').lower()}"
        for pattern in self.years_patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            try:
                years = int(match.group(1))
            except (ValueError, IndexError):
                continue
            if years >= self.min_years:
                return "experiencia_excesiva"
        return None


class TrustFilter:
    """RF-4 y RF-5 (spec 001): empresas bloqueadas y señales de scam."""

    def __init__(self, cfg: dict):
        self.blocked_companies: list[str] = [
            re.sub(r"[^a-z0-9]", "", c.lower()) for c in cfg.get("blocked_companies", [])
        ]
        self.scam_signals: list[str] = [s.lower() for s in cfg.get("scam_signals", [])]

    def check(self, title: str, company: str, description: str) -> str | None:
        company_norm = re.sub(r"[^a-z0-9]", "", (company or "").lower())
        for blocked in self.blocked_companies:
            if blocked and blocked in company_norm:
                return "empresa_bloqueada"
        text = f"{title} {company} {description}".lower()
        for signal in self.scam_signals:
            if signal and signal in text:
                return "senal_scam"
        return None


class LanguageFilter:
    """RF-6 y RF-7 (spec 001): nivel de inglés exigido y bono por mercado hispano."""

    def __init__(self, cfg: dict):
        self.rejected_patterns: list[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in cfg.get("rejected_english_patterns", [])
        ]
        self.spanish_markers: list[str] = [s.lower() for s in cfg.get("spanish_markers", [])]
        self.spanish_bonus: float = float(cfg.get("spanish_bonus", 0))

    def check_english(self, title: str, description: str) -> str | None:
        text = f"{title} {description}"
        for pattern in self.rejected_patterns:
            if pattern.search(text):
                return "idioma_no_alcanzado"
        return None

    def is_spanish_market(self, title: str, description: str, location: str) -> bool:
        text = f"{title} {description} {location}".lower()
        return any(marker in text for marker in self.spanish_markers)
