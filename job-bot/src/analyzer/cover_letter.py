from typing import Optional
from src.scrapers.base import JobPost
from src.profile import profile


class CoverLetterGenerator:
    def __init__(self, openai_api_key: str = ""):
        self.openai_api_key = openai_api_key

    def generate(self, job: JobPost) -> str:
        if self.openai_api_key:
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
            f"CI/CD pipelines with GitHub Actions and Azure, ensuring that every release "
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
        try:
            import openai
            openai.api_key = self.openai_api_key
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un asistente que escribe cartas de presentación profesionales en inglés."},
                    {"role": "user", "content": (
                        f"Write a professional cover letter for this job:\n"
                        f"Title: {job.title}\nCompany: {job.company}\n"
                        f"Description: {job.description[:1500]}\n\n"
                        f"Candidate profile: {profile.experience_summary}\n"
                        f"Skills: {', '.join(profile.skills)}\n"
                        f"Name: {profile.name}\n"
                        f"English level: {profile.english_level}\n"
                        f"Location: {profile.location}\n"
                        f"Keep it concise (max 300 words) and professional."
                    )}
                ],
                max_tokens=500,
                temperature=0.7
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return self._generate_template(job)

    def _extract_matched_skills(self, job: JobPost) -> list:
        text = f"{job.title.lower()} {job.description.lower()}"
        return [s for s in profile.skills if s.lower() in text]
