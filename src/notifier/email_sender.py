import smtplib
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.notifier.template import generar_html, generar_texto
from src.profile import profile
from src.scrapers.base import JobPost


class EmailNotifier:
    def __init__(self, from_addr: str, password: str, to_addr: str,
                 smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
        self.from_addr = from_addr
        self.password = password
        self.to_addr = to_addr
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def send_jobs_report(self, jobs: list[JobPost]) -> bool:
        fecha = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        html = generar_html(jobs, fecha)
        text = generar_texto(jobs, fecha)

        count = len(jobs)
        if count > 0:
            subject = f"Job Bot Report - {count} {'new match' if count == 1 else 'new matches'} found"
        else:
            subject = "Job Bot Report - No matches today"

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{profile.name} Job Bot <{self.from_addr}>"
            msg["To"] = self.to_addr
            msg.attach(MIMEText(text, "plain", "utf-8"))
            msg.attach(MIMEText(html, "html", "utf-8"))

            if int(self.smtp_port) == 465:  # SSL directo (Gmail 465)
                with smtplib.SMTP_SSL(self.smtp_server, 465, timeout=30) as server:
                    server.login(self.from_addr, self.password)
                    server.send_message(msg)
            else:  # STARTTLS (587)
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                    server.starttls()
                    server.login(self.from_addr, self.password)
                    server.send_message(msg)
            return True
        except Exception as e:  # noqa: BLE001
            print(f"  Email error: {e}")
            return False
