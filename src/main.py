import sys
from datetime import datetime, timezone
from typing import List
from src.config import config
from src.scrapers.base import JobPost
from src.scrapers.remoteok import RemoteOKScraper
from src.scrapers.weworkremotely import WeWorkRemotelyScraper
from src.scrapers.remotive import RemotiveScraper
from src.scrapers.linkedin import LinkedInScraper
from src.scrapers.indeed import IndeedScraper
from src.scrapers.reddit import RedditScraper
from src.scrapers.getonboard import GetOnBoardScraper
from src.analyzer.matcher import JobMatcher
from src.analyzer.cover_letter import CoverLetterGenerator
from src.notifier.email_sender import EmailNotifier
from src.storage.database import JobDatabase


def get_scrapers():
    scrapers = [
        RemoteOKScraper(),
        WeWorkRemotelyScraper(),
        RemotiveScraper(),
        IndeedScraper(),
        GetOnBoardScraper(),
        RedditScraper(
            client_id=config.reddit_client_id,
            client_secret=config.reddit_client_secret,
            user_agent=config.reddit_user_agent
        ),
    ]
    if config.linkedin_email and config.linkedin_password:
        scrapers.append(LinkedInScraper())
    else:
        scrapers.append(LinkedInScraper({"li_at": ""}))
    return scrapers


def scrape_all(scrapers, keywords: List[str]) -> List[JobPost]:
    all_jobs = []
    for scraper in scrapers:
        try:
            print(f"  [{scraper.name}] scraping...")
            jobs = scraper.scrape(keywords)
            active_jobs = []
            for job in jobs:
                if not scraper.verify_job_active(job.url):
                    print(f"    Skipping closed: {job.title} @ {job.company}")
                    continue
                if not job.posted_date or scraper.is_recent(job, config.max_days_old):
                    active_jobs.append(job)
            print(f"  [{scraper.name}] {len(active_jobs)} active jobs (from {len(jobs)} total)")
            all_jobs.extend(active_jobs)
        except Exception as e:
            print(f"  [{scraper.name}] Error: {e}")
    return all_jobs


def main():
    print("=" * 60)
    print(f"Job Scraper Bot - {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    db = JobDatabase(config.mongo_uri, config.mongo_db)
    if not db.is_connected():
        print("WARNING: MongoDB not available, running without persistence")
    else:
        print("MongoDB connected")

    scrapers = get_scrapers()
    print(f"\nScraping {len(scrapers)} platforms...")
    all_jobs = scrape_all(scrapers, config.search_keywords)
    print(f"\nTotal raw jobs: {len(all_jobs)}")

    matcher = JobMatcher()
    seen_urls = set()
    deduped = []
    for j in all_jobs:
        if j.url not in seen_urls:
            seen_urls.add(j.url)
            deduped.append(j)
    print(f"After dedup: {len(deduped)} jobs (from {len(all_jobs)})")

    filtered = matcher.filter_jobs(deduped)
    print(f"After filtering: {len(filtered)} jobs")

    if not filtered:
        print("No matching jobs found")
        if db.is_connected():
            db.close()
        return

    cover_gen = CoverLetterGenerator(openai_api_key=config.openai_api_key)
    new_jobs = []
    for job in filtered:
        if db.is_connected() and db.is_duplicate(job.url):
            continue
        job.cover_letter = cover_gen.generate(job)
        if db.is_connected():
            db.save_job({
                "title": job.title, "company": job.company,
                "location": job.location, "description": job.description,
                "url": job.url, "source": job.source,
                "posted_date": job.posted_date.isoformat() if job.posted_date else None,
                "match_score": job.match_score, "cover_letter": job.cover_letter,
                "apply_url": job.apply_url
            })
        new_jobs.append(job)

    print(f"\nNew jobs to report: {len(new_jobs)}")

    if new_jobs:
        print("\n--- TOP MATCHES ---")
        for j in new_jobs[:10]:
            print(f"  [{int(j.match_score*100)}%] {j.title} @ {j.company} ({j.source})")
            print(f"       {j.url}")
            print(f"       Cover letter generated: {len(j.cover_letter or '')} chars")

    if config.email_from and config.email_password:
        print("\nSending email report...")
        notifier = EmailNotifier(
            from_addr=config.email_from,
            password=config.email_password,
            to_addr=config.email_to
        )
        notifier.send_jobs_report(new_jobs)
        print("Email sent")
        if db.is_connected():
            db.mark_all_sent()
    else:
        print("\nEmail not configured - results printed above")
        print("Set EMAIL_FROM and EMAIL_PASSWORD env vars to enable email delivery")

    if db.is_connected():
        db.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
