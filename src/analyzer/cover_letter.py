import requests

from src.profile import cv_skills, profile
from src.scrapers.base import JobPost


class CoverLetterGenerator:
    def __init__(self, gemini_api_key: str = "", model: str = "gemini-3.8-flash"):
        self.gemini_api_key = gemini_api_key
        self.model = model

    def generate(self, job: JobPost) -> str:
        if self.gemini_api_key:
            return self._generate_ai(job)
        return self._generate_template(job)

    def _generate_template(self, job: JobPost) -> str:
        matched_skills = self._extract_matched_skills(job)
        skills_text = ", ".join(matched_skills[:5]) if matched_skills else "test automation and front-end development"

        return (
            f"Dear Hiring Manager at {job.company},\n\n"
            f"I am writing to express my strong interest in the {job.title} position. "
            f"As a QA Automation Engineer and Front-End Developer with experience in "
            f"{skills_text}, I am confident that my technical background and passion for "
            f"quality software make me an excellent fit for this role.\n\n"
            f"My expertise includes building end-to-end test automation frameworks using "
            f"Cypress and Playwright, performing API testing with Postman, and developing "
            f"responsive React applications with TypeScript. I have experience integrating "
            f"CI/CD pipelines with GitHub Actions and Azure DevOps, ensuring that every release "
            f"is thoroughly validated before reaching production.\n\n"
            f"I am particularly drawn to this position because it aligns with my dual "
            f"passion for development and quality assurance. I believe that great software "
            f"is built by teams that value both innovation and reliability.\n\n"
            f"I would welcome the opportunity to discuss how my skills and experience can "
            f"contribute to {job.company}'s success. Thank you for considering my application.\n\n"
            f"Best regards,\n{profile.name}\n"
            f"{profile.email}\n"
            f"{profile.linkedin}\n"
            f"{profile.github}"
        )

    def _generate_ai(self, job: JobPost) -> str:
        """RF-14: Gemini reemplaza a OpenAI; cualquier fallo vuelve a la
        plantilla para no interrumpir el reporte."""
        try:
            resp = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model}:generateContent",
                params={"key": self.gemini_api_key},
                json={
                    "contents": [{"parts": [{"text": self._ai_prompt(job)}]}],
                    "generationConfig": {"maxOutputTokens": 700, "temperature": 0.7},
                },
                timeout=30,
            )
            resp.raise_for_status()
            parts = resp.json()["candidates"][0]["content"]["parts"]
            text = parts[0]["text"].strip()
            return text or self._generate_template(job)
        except Exception:  # noqa: BLE001
            return self._generate_template(job)

    def _ai_prompt(self, job: JobPost) -> str:
        return (
            "Escribe una carta de presentación profesional en inglés para este empleo:\n"
            f"Title: {job.title}\nCompany: {job.company}\n"
            f"Description: {job.description[:1500]}\n\n"
            f"Candidate profile: {profile.experience_summary}\n"
            f"Skills: {', '.join(profile.skills)}\n"
            f"Name: {profile.name}\n"
            f"English level: {profile.english_level}\n"
            f"Location: {profile.location}\n"
            "Keep it concise (max 300 words) and professional."
        )

    def _extract_matched_skills(self, job: JobPost) -> list:
        """RF-11 (spec 001): skills desde cvs/profile.json, nunca desde
        listas por defecto de código."""
        text = f"{job.title.lower()} {job.description.lower()}"
        return [s for s in cv_skills() if s.lower() in text]
