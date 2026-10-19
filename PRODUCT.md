# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS with no build step, served by GitHub Pages from `docs/`. Data comes from `docs/data/jobs.json`, written by the bot (`src/exporter.py`) on every daily GitHub Actions run.

## Users

José Eduardo Jiménez, the only user. He is a QA Automation Engineer (Cypress/Playwright, ~2 years) and UI/graphic designer from Barquisimeto, Venezuela, looking for 100% remote work. He opens the page after the daily email to decide what to apply to and to apply.

## Product Purpose

Turn the bot's daily scrape and the manually curated research into a short, honest list of offers he can actually apply to, and make applying fast. Success means he applies to the good offers the same day and never wastes time on offers that are senior-only, geo-restricted or in another language.

## Positioning

A personal application desk, not a job board. It shows only offers that already passed his own filters (level, location, language, trust), says why each one fits or what is missing, and lets him act from the same row.

## Operating Context

- Daily email "Job Bot Report" links to this page.
- Sources: LinkedIn, Torre (Venezuela board), Get on Board, WeRemoto, Jobgether, Upwork, Indeed, recruiter emails.
- Some offers are applied to by sending the CV by email; those open a pre-filled Gmail draft from jose.e.jimenez.1411@gmail.com. José attaches the CV and presses Send himself.
- Applied/hidden state is personal and lives in the browser (localStorage).

## Capabilities and Constraints

- Filter by family (QA, frontend, design, admin) and source; search; mark as applied; hide.
- No backend, no secrets, no automatic sending.
- Spanish UI.

## Evidence on Hand

- Real offers in `docs/data/jobs.json` (curated set from 2026-10-15/19 research plus bot output).
- CVs in `cvs/` (QA CV in Spanish, HYBRID CV in English).

## Product Principles

1. Fewer, better: show only what passed the filters, best first.
2. Honest fit: every row says what matches and what is missing.
3. Act in place: open the posting or the email draft from the row.
4. Never send anything on his behalf.
