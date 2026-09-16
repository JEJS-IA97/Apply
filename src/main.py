from datetime import datetime, timezone
from typing import List
from src.config import config
from src.scrapers.base import JobPost
from src.scrapers.remoteok import RemoteOKScraper
from src.scrapers.weworkremotely import WeWorkRemotelyScraper
from src.scrapers.remotive import RemotiveScraper
from src.scrapers.arbeitnow import ArbeitnowScraper
from src.scrapers.himalayas import HimalayasScraper
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
        RemotiveScraper(),
        WeWorkRemotelyScraper(),
        ArbeitnowScraper(),
        HimalayasScraper(),
        IndeedScraper(),
        GetOnBoardScraper(),
        RedditScraper(
            client_id=config.reddit_client_id,
            client_secret=config.reddit_client_secret,
            user_agent=config.reddit_user_agent
        ),
    ]
    scrapers.append(LinkedInScraper(email=config.linkedin_email, password=config.linkedin_password))
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
                    continue
                if not job.posted_date or scraper.is_recent(job, config.max_days_old):
                    active_jobs.append(job)
            print(f"  [{scraper.name}] {len(active_jobs)} active (from {len(jobs)} raw)")
            all_jobs.extend(active_jobs)
        except Exception as e:
            print(f"  [{scraper.name}] Error: {e}")
    return all_jobs


def dedup_jobs(jobs: List[JobPost]) -> List[JobPost]:
    seen = set()
    result = []
    for j in jobs:
        key = f"{j.title.lower().strip()}|{j.company.lower().strip()}"
        if key not in seen:
            seen.add(key)
            result.append(j)
    return result


def main():
    print("=" * 60)
    print(f"Job Scraper Bot - {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    db = JobDatabase(config.mongo_uri, config.mongo_db)
    if not db.is_connected():
        print("WARNING: MongoDB not available, running without persistence")

    scrapers = get_scrapers()
    print(f"\nScraping {len(scrapers)} platforms...")
    all_jobs = scrape_all(scrapers, config.search_keywords)
    print(f"\nTotal raw: {len(all_jobs)}")

    deduped = dedup_jobs(all_jobs)
    print(f"After title+company dedup: {len(deduped)}")

    matcher = JobMatcher()
    filtered = matcher.filter_jobs(deduped)
    print(f"After CV matching (score>=20): {len(filtered)}")

    if not filtered:
        print("No matching jobs found")
        if db.is_connected():
            db.close()
        return

    new_jobs = []
    for job in filtered:
        if db.is_connected() and db.is_duplicate(job.url):
            continue
        new_jobs.append(job)

    print(f"New (not in DB): {len(new_jobs)}")

    if not new_jobs:
        print("All jobs already sent previously")
        if db.is_connected():
            db.close()
        return

    cover_gen = CoverLetterGenerator(openai_api_key=config.openai_api_key)
    for job in new_jobs:
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

    print(f"\n--- TOP {len(new_jobs)} MATCHES ---")
    for j in new_jobs[:15]:
        print(f"  [{j.match_score}%] {j.title} @ {j.company} ({j.source}) | {j.location}")

    if config.email_from and config.email_password:
        notifier = EmailNotifier(
            from_addr=config.email_from,
            password=config.email_password,
            to_addr=config.email_to
        )
        sent = notifier.send_jobs_report(new_jobs)
        print(f"\nEmail {'sent' if sent else 'FAILED'}")
        if db.is_connected():
            db.mark_all_sent()

    if db.is_connected():
        db.close()

    print("Done!")


if __name__ == "__main__":
    main()
