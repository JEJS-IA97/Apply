# Job Scraper Bot

Scrapes job postings from multiple platforms, filters by your profile, generates cover letters, and emails you a daily report at 8 AM.

## Platforms

- **[RemoteOK](https://remoteok.com)** - Remote jobs API
- **[Remotive](https://remotive.com)** - Remote jobs API
- **[We Work Remotely](https://weworkremotely.com)** - Remote jobs
- **[Indeed](https://indeed.com)** - Scraped with requests+BS4
- **[LinkedIn](https://linkedin.com)** - Guest API scraping
- **[GetOnBoard](https://getonbrd.com)** - LatAm tech jobs
- **[Reddit](https://reddit.com)** - r/remotejs, r/forhire, r/jobbit, r/remotejobs, r/QualityAssurance

## Setup

1. Clone the repo
2. Copy `.env.example` to `.env` and fill in your credentials
3. Install: `pip install -r requirements.txt`
4. Run: `python -m src.main`

## Filters

- Remote-only (no hybrid/on-site)
- Excludes India and all of Asia
- Matches your skills (Cypress, Playwright, React, Python, etc.)
- Verifies jobs are still active (checks for apply button)
- Deduplicates across platforms

## GitHub Actions (Free Cron)

The workflow runs daily at 12:00 UTC (8:00 AM Venezuela time). Set these **repository secrets**:

| Secret | Description |
|--------|-------------|
| `EMAIL_FROM` | Your Gmail address |
| `EMAIL_PASSWORD` | Gmail App Password (not your regular password!) |
| `EMAIL_TO` | jose.e.jimenez.1411@gmail.com |
| `MONGO_URI` | MongoDB Atlas connection string (optional) |
| `REDDIT_CLIENT_ID` | Reddit API client ID (optional) |
| `REDDIT_CLIENT_SECRET` | Reddit API secret (optional) |
| `OPENAI_API_KEY` | OpenAI key for AI cover letters (optional) |

### Getting a Gmail App Password
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to "App passwords"
4. Generate one for "Mail"
5. Use that as `EMAIL_PASSWORD`

## Cover Letters

Two modes:
- **Template mode** (default): fills in job details into a professional template
- **AI mode** (with `OPENAI_API_KEY`): generates unique cover letters via GPT

## Local Test

```bash
python -m src.main
```
