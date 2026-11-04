"""RF-14 (spec 004): lee los grupos y canales de Telegram que José configura
en TELEGRAM_CHATS, con su propia sesión (TELEGRAM_SESSION). Solo lee: nunca
escribe ni reacciona en los chats."""
import asyncio
import importlib.util
import re
from datetime import UTC, datetime, timedelta

from src.exporter import extract_apply_email
from src.scrapers.base import BaseScraper, JobPost

URL_RE = re.compile(r"https?://[^\s)>\]\"']+")
HIRE_RE = re.compile(
    r"(vacante|contrata|buscamos|se busca|estamos buscando|hiring|we.?re hiring|oferta de empleo|"
    r"oportunidad laboral|postula|apply|job opening|empleo)", re.IGNORECASE)
REMOTE_RE = re.compile(r"(remot|home ?office|teletrabajo|work from home|anywhere|desde casa)", re.IGNORECASE)


def telethon_available() -> bool:
    return importlib.util.find_spec("telethon") is not None


def parse_chats(raw: str) -> list[int | str | tuple[int | str, int]]:
    """"-1004380156934, @canal, t.me/otro, -1004380156934_9" ->
    [-1004380156934, "canal", "otro", (-1004380156934, 9)]. El sufijo _N es un
    tema (topic) de un grupo con foros, como lo muestra web.telegram.org."""
    chats: list[int | str | tuple[int | str, int]] = []
    for token in re.split(r"[,\s;]+", raw or ""):
        token = token.strip().rstrip("/")
        if not token:
            continue
        token = re.sub(r"^(https?://)?(t\.me/|web\.telegram\.org/\w/#)", "", token).lstrip("@")
        topic = None
        m = re.fullmatch(r"(-?\d+)_(\d+)", token)
        if m:
            token, topic = m.group(1), int(m.group(2))
        chat = int(token) if token.lstrip("-").isdigit() else token
        chats.append((chat, topic) if topic else chat)
    return chats


def _title(text: str) -> str:
    for line in text.splitlines():
        clean = re.sub(r"[^\w\s/&+.,:()–-]", "", line).strip(" -–:*")
        if len(clean) >= 6:
            return clean[:120]
    return text.strip()[:120]


def message_to_job(text: str, date: datetime, chat_title: str, link: str) -> JobPost | None:
    """Convierte un mensaje en JobPost si parece una vacante."""
    if not text or len(text) < 40 or not HIRE_RE.search(text):
        return None
    external = [u.rstrip(".,") for u in URL_RE.findall(text) if "t.me/" not in u]
    url = external[0] if external else link
    remote = bool(REMOTE_RE.search(text))
    return JobPost(
        title=_title(text), company=chat_title, location="Remote" if remote else "",
        description=text[:3000], url=url, source="Telegram", posted_date=date,
        is_remote=remote, apply_url=url, post_source=True, apply_email=extract_apply_email(text),
    )


class TelegramScraper(BaseScraper):
    trusts_freshness = True  # la frescura la valida RF-15 (analyzer/freshness.py)
    max_requests = 1

    def __init__(self, api_id: str, api_hash: str, session: str, chats: list[int | str],
                 days: int = 7, per_chat: int = 300):
        super().__init__("Telegram")
        self.api_id, self.api_hash, self.session = api_id, api_hash, session
        self.chats, self.days, self.per_chat = chats, days, per_chat

    def scrape(self, keywords: list[str]) -> list[JobPost]:
        try:
            return asyncio.run(self._fetch())
        except Exception as exc:  # noqa: BLE001
            self.disabled_reason = f"Telegram no disponible: {exc}"
            return []

    async def _fetch(self) -> list[JobPost]:
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        since = datetime.now(UTC) - timedelta(days=self.days)
        jobs: list[JobPost] = []
        async with TelegramClient(StringSession(self.session), int(self.api_id), self.api_hash) as client:
            if not await client.is_user_authorized():
                self.disabled_reason = "TELEGRAM_SESSION inválida o expirada: ejecuta scripts/telegram_login.py"
                return []
            await client.get_dialogs(limit=500)  # carga en caché los chats por id
            for item in self.chats:
                chat, topic = item if isinstance(item, tuple) else (item, None)
                try:
                    entity = await client.get_entity(chat)
                except (ValueError, TypeError) as exc:
                    print(f"    [Telegram] chat {chat} no accesible: {exc}")
                    continue
                title = getattr(entity, "title", None) or str(chat)
                if topic:
                    title = f"{title} #{topic}"
                username = getattr(entity, "username", None)
                async for msg in client.iter_messages(entity, limit=self.per_chat, reply_to=topic):
                    if msg.date and msg.date < since:
                        break
                    link = (f"https://t.me/{username}/{msg.id}" if username
                            else f"https://t.me/c/{entity.id}/{msg.id}")
                    job = message_to_job(msg.message or "", msg.date, title, link)
                    if job:
                        jobs.append(job)
        return jobs

    def verify_job_active(self, url: str) -> bool:
        return True
