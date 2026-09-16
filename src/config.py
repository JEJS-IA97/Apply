import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()


def env(key: str, default: str = "") -> str:
    val = os.getenv(key)
    return val if val else default


@dataclass
class Config:
    mongo_uri: Optional[str] = env("MONGO_URI") or None
    mongo_db: str = env("MONGO_DB", "job_bot")
    email_from: str = env("EMAIL_FROM")
    email_password: str = env("EMAIL_PASSWORD")
    email_to: str = env("EMAIL_TO", "jose.e.jimenez.1411@gmail.com")
    smtp_server: str = env("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(env("SMTP_PORT", "587"))
    linkedin_email: str = env("LINKEDIN_EMAIL")
    linkedin_password: str = env("LINKEDIN_PASSWORD")
    openai_api_key: str = env("OPENAI_API_KEY")
    telegram_api_id: str = env("TELEGRAM_API_ID")
    telegram_api_hash: str = env("TELEGRAM_API_HASH")
    telegram_phone: str = env("TELEGRAM_PHONE")
    reddit_client_id: str = env("REDDIT_CLIENT_ID")
    reddit_client_secret: str = env("REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = env("REDDIT_USER_AGENT", "job-bot/1.0")
    search_keywords: List[str] = field(default_factory=lambda: [
        "QA Automation Engineer", "QA Engineer", "Automation Engineer",
        "Frontend Developer", "Frontend Engineer", "SDET",
        "Software Development Engineer in Test", "Quality Assurance Automation",
        "React Developer", "Playwright", "Cypress",
        "QA Analyst", "Quality Assurance", "Manual QA",
        "QA Tester", "Automation Tester"
    ])
    exclude_locations: List[str] = field(default_factory=lambda: [
        "India", "Asia", "Bangalore", "Mumbai", "Hyderabad", "Chennai",
        "Pune", "Delhi", "Kolkata", "Ahmedabad", "Noida", "Gurgaon",
        "Philippines", "Pakistan", "Bangladesh", "Sri Lanka", "Vietnam",
        "Indonesia", "Thailand", "Malaysia", "China", "Singapore"
    ])
    exclude_terms: List[str] = field(default_factory=lambda: [
        "hybrid", "on-site", "onsite", "senior staff", "principal"
    ])
    max_days_old: int = int(os.getenv("MAX_DAYS_OLD", "7"))
    output_format: str = os.getenv("OUTPUT_FORMAT", "email")


config = Config()
