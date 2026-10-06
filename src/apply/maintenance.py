"""RF-6/RF-7 (spec 003): estado de mantenimiento de las familias ATS.

Cuando un selector falla en producción, la familia se marca
``validated: false`` en ``storage/family_status.json`` y deja de
recibir envíos hasta revalidarse manualmente (se elimina la entrada).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.apply.registry import FAMILIES

DEFAULT_PATH = Path("storage/family_status.json")


def _family(name: str):
    return next((f for f in FAMILIES if f.name == name), None)


class FamilyStatus:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else DEFAULT_PATH

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        text = self.path.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        data = json.loads(text)
        if not isinstance(data, dict):
            raise TypeError(f"estado corrupto (se espera un objeto): {self.path}")
        return data

    def is_active(self, name: str) -> bool:
        family = _family(name)
        if family is None or not family.can_submit:
            return False
        entry = self.load().get(name) or {}
        return entry.get("validated", True) is not False

    def demote(self, name: str, reason: str) -> None:
        data = self.load()
        data[name] = {
            "validated": False,
            "reason": reason,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)
