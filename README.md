# Job Scraper Bot

> Este proyecto sigue **Spec-Driven Development (SDD)**: ver `AGENTS.md` (contrato del agente), `docs/constitution.md` (principios), `docs/sdd.md` (metodología) y `specs/` (alcance aprobado por feature).

Scrapes job postings from multiple platforms and hiring posts, filters them against your CV profile, generates cover letters, and emails you a daily report. Postulation is **assisted by default** (no application is sent); with `APPLY_MODE=auto` it sends on the supported ATS pilot — see "Apply mode".

## Sources (`src/scrapers/registry.py` is the single source of truth)

**Enabled (10):** Remotive, We Work Remotely, Arbeitnow, Himalayas, LinkedIn (guest API), HackerNews (job board + hiring threads), Mastodon (hiring hashtags), Web3Career, InfoJobs (Spanish listings), BuiltIn.

**Gated (credentials required, `disabled` with cause until provided):**
- Reddit — needs `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET` (subs and searches come from `cvs/profile.json`).
- LinkedIn posts — needs LinkedIn credentials + Playwright (used only to *read* hiring posts).

**Blocked/disabled with verified cause (examples):** RemoteOK (scam verdict, spec 002 RF-12), Indeed/Dice/Bluesky/FlexJobs (403), GetOnBoard/Toptal (404), Welcome to the Jungle (anti-bot 202), InfoJobs/CAPTCHA sources stop themselves when challenged (we do not bypass anti-bot defenses — ethics P3).

Every source that is not consulted appears in the run log with its cause.

## Filters (profile-driven, `cvs/profile.json`)

Applied in order: trust (scams, blocked employers, employment-agency/IAM-recruiting signals) → language (Spanish/English, Latino country codes) → level (junior/mid only; senior/sr/lead/staff/II-IV excluded) → years of experience vs. CV → role relevance (QA/automation/frontend/DevOps families and `job_titles_fit`, score ≥ 20) → remote-only + geography (India and Asia excluded) → dedup (canonical URL, then title+company). Exclusions are printed per reason at the end of each run.

## Cover letters

- **Template mode** (default): fills job details into a template; skills come from `cvs/profile.json`.
- **AI mode** (with `GEMINI_API_KEY`): Gemini-generated letters (falls back to the template on any error).

## Apply mode (`APPLY_MODE`)

| Value | Behavior |
|-------|----------|
| `assist` (default) | Report includes link, profile data, cover letter and a manual-review checklist. No application is sent. |
| `off` | Report only, no checklist block. |
| `auto` | Sends applications for already-filtered matches on the supported ATS pilot (Greenhouse first), capped by `APPLY_DAILY_LIMIT` and recorded in `storage/applications.json`. Stops on visible CAPTCHA/login (RF-7). Falls back to `assist` if Playwright/Chromium is unavailable (nothing is sent). |

`APPLY_DAILY_LIMIT` (default 5) caps sends per run and per day. `APPLY_PAUSED=1` suspends `auto` for a run without changing mode.

## Setup

1. Clone the repo
2. Copy `.env.example` to `.env` and fill in your credentials
3. Install: `pip install -r requirements.txt`
4. Install the browser for `auto` (and LinkedIn-posts reading): `python -m playwright install chromium`
5. Run: `python -m src.main`

## Verification

```bash
python -m pytest        # tests
python -m ruff check src tests   # lint
```

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
| `GEMINI_API_KEY` | Google Gemini key for AI cover letters (optional) |
| `APPLY_MODE` | `assist` (default) / `off` / `auto` (sends on the ATS pilot; needs `python -m playwright install chromium`) |

### Getting a Gmail App Password
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to "App passwords"
4. Generate one for "Mail"
5. Use that as `EMAIL_PASSWORD`
