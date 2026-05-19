from dataclasses import dataclass, field
from typing import List


@dataclass
class UserProfile:
    name: str = "José Eduardo Jiménez"
    email: str = "jose.e.jimenez.1411@gmail.com"
    title: str = "QA Automation Engineer / Front-End Developer"
    location: str = "Venezuela"
    english_level: str = "B1-B2 (Intermediate)"
    linkedin: str = "https://www.linkedin.com/in/jejs97"
    github: str = "https://github.com/JEJS-IA97"
    portfolio: str = "https://jejs-ia97.github.io/Portfolio/"
    telegram: str = "https://t.me/JEJS97"
    discord: str = "jejs8519"

    skills: List[str] = field(default_factory=lambda: [
        "Cypress", "Playwright", "Selenium", "Postman", "Appium",
        "Pytest", "Cucumber", "React", "React Native", "JavaScript",
        "TypeScript", "Python", "Node.js", "HTML", "CSS", "TailwindCSS",
        "Vite", "MongoDB", "MySQL", "PostgreSQL", "SQLite",
        "Azure", "Git", "GitHub Actions", "CI/CD", "REST API testing",
        "E2E testing", "API automation", "Page Object Model",
        "JWT authentication", "Socket.io"
    ])

    experience_summary: str = (
        "QA Automation Engineer with strong Front-End development background. "
        "Experienced in building test automation frameworks with Cypress and Playwright, "
        "REST API testing with Postman, and CI/CD integration. Also skilled in React "
        "development with TypeScript and modern frontend tooling. Passionate about "
        "delivering robust, well-tested software with great UX."
    )

    work_preferences: dict = field(default_factory=lambda: {
        "remote_only": True,
        "exclude_india_asia": True,
        "job_types": ["Full-time", "Contract", "Freelance"],
        "min_salary_usd": None
    })


profile = UserProfile()
