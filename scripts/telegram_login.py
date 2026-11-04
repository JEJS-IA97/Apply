"""RF-14 (spec 004): inicio de sesión único en Telegram.

Ejecútalo TÚ en tu PC (no en GitHub Actions):
    python scripts/telegram_login.py

Usa TELEGRAM_API_ID, TELEGRAM_API_HASH y TELEGRAM_PHONE del .env. Telegram te
enviará un código a la app; escríbelo aquí (y tu contraseña de 2 pasos si la
tienes). Al final imprime TELEGRAM_SESSION: guárdalo en tu .env y como secret
de GitHub. Esa cadena da acceso a tu cuenta: no la compartas ni la subas al repo.
También lista tus chats con su id, para que confirmes TELEGRAM_CHATS.
"""
import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession

from src.config import config


async def main() -> None:
    async with TelegramClient(StringSession(), int(config.telegram_api_id), config.telegram_api_hash) as client:
        await client.start(phone=config.telegram_phone or None)
        print("\nChats (id  ·  nombre):")
        async for d in client.iter_dialogs(limit=200):
            if d.is_group or d.is_channel:
                print(f"  {d.id}  ·  {d.name}")
        print("\nTELEGRAM_SESSION=" + client.session.save())


if __name__ == "__main__":
    asyncio.run(main())
