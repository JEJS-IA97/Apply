import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "job_bot")
    email_from: str = os.getenv("EMAIL_FROM", "")
    email_password: str = os.getenv("EMAIL_PASSWORD", "")
    email_to: str = os.getenv("EMAIL_TO", "jose.e.jimenez.1411@gmail.com")
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    linkedin_email: str = os.getenv("LINKEDIN_EMAIL", "")
    linkedin_password: str = os.getenv("LINKEDIN_PASSWORD", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    telegram_api_id: str = os.getenv("TELEGRAM_API_ID", "")
    telegram_api_hash: str = os.getenv("TELEGRAM_API_HASH", "")
    telegram_phone: str = os.getenv("TELEGRAM_PHONE", "")
    reddit_client_id: str = os.getenv("REDDIT_CLIENT_ID", "")
    reddit_client_secret: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    reddit_user_agent: str = os.getenv("REDDIT_USER_AGENT", "job-bot/1.0")
    search_keywords: List[str] = field(default_factory=lambda: [
        "QA Automation Engineer", "QA Engineer", "Automation Engineer",
        "Frontend Developer", "Frontend Engineer", "SDET",
        "Software Development Engineer in Test", "Quality Assurance Automation",
        "React Developer", "Playwright", "Cypress"
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
