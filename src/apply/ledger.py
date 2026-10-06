"""RF-8 (spec 003): registro auditable de los intentos de postulación.

Cada intento que llegó a la ruta de envío (enviado, dato_faltante o
error) queda en ``storage/applications.json`` con oferta, dominio,
fecha, resultado y motivo. ``dominio_no_soportado`` no es un intento y
no se registra. Los envíos cuentan para el límite diario (RF-4).
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from src.apply.runner import ApplyResult
from src.scrapers.base import JobPost

DEFAULT_PATH = Path("storage/applications.json")


def entry_for(
    job: JobPost,
    ats_url: str,
    result: ApplyResult,
    timestamp: datetime | None = None,
) -> dict:
    moment = timestamp or datetime.now(timezone.utc)
    return {
        "job_url": job.url,
        "apply_url": job.apply_url or "",
        "ats_url": ats_url or "",
        "domain": urlparse(ats_url or "").netloc.lower().removeprefix("www."),
        "title": job.title,
        "company": job.company,
        "family": result.family,
        "outcome": result.outcome,
        "detail": result.detail,
        "confirmation_url": result.confirmation_url or "",
        "timestamp": moment.isoformat(),
    }


def save_evidence(result: ApplyResult, directory: Path) -> str | None:
    """RF-3: persiste la captura/HTML de confirmación de un envío.

    El archivo queda junto al registro (``storage/evidence/`` en
    producción, el directorio del ledger en tests) y su ruta se guarda
    en la entrada como ``evidence_path``.
    """
    html = (result.evidence or "").strip()
    if not html:
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-z0-9]+", "-", (result.family or "ats").lower()).strip("-") or "ats"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stamp}-{slug}-{uuid4().hex[:8]}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


class ApplicationLedger:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else DEFAULT_PATH

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        text = self.path.read_text(encoding="utf-8").strip()
        if not text:
            return []
        data = json.loads(text)
        if not isinstance(data, list):
            raise TypeError(f"registro corrupto (se espera una lista): {self.path}")
        return data

    def record(self, entry: dict) -> None:
        entries = self.load()
        entries.append(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, self.path)

    def sent_today(self, now: datetime | None = None) -> int:
        moment = now or datetime.now(timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        today = moment.date()
        count = 0
        for entry in self.load():
            if entry.get("outcome") != "enviado":
                continue
            try:
                stamp = datetime.fromisoformat(entry["timestamp"])
            except (KeyError, TypeError, ValueError):
                continue
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            if stamp.date() == today:
                count += 1
        return count
