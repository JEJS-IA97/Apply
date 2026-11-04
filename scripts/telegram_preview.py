"""RF-14 (spec 004): lee tus chats de Telegram (últimos 7 días) y guarda las
vacantes encontradas en ../_telegram_preview.json (fuera del repo) para revisarlas.

Uso (PowerShell, dentro de apply):  python -m scripts.telegram_preview
"""
import json
from pathlib import Path

from src.config import config
from src.scrapers.telegram import TelegramScraper, parse_chats


def main() -> None:
    chats = parse_chats(config.telegram_chats)
    scraper = TelegramScraper(config.telegram_api_id, config.telegram_api_hash, config.telegram_session, chats, days=7)
    jobs = scraper.scrape([])
    out = Path("..") / "_telegram_preview.json"
    out.write_text(json.dumps([{
        "chat": j.company, "fecha": j.posted_date.isoformat() if j.posted_date else "",
        "titulo": j.title, "url": j.url, "correo": j.apply_email or "", "texto": j.description[:1500],
    } for j in jobs], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Chats: {len(chats)} | vacantes (7 días): {len(jobs)} | {scraper.disabled_reason or 'ok'}")
    print(f"Guardado en {out.resolve()}")


if __name__ == "__main__":
    main()
