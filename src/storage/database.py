from datetime import datetime, timezone
from typing import List, Optional
from pymongo import MongoClient, errors


class JobDatabase:
    def __init__(self, uri: str, db_name: str):
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.jobs = self.db["jobs"]
        self.seen = self.db["seen_urls"]
        self.jobs.create_index("url", unique=True)
        self.seen.create_index("url", unique=True)

    def is_connected(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except errors.ConnectionFailure:
            return False

    def is_duplicate(self, url: str) -> bool:
        return self.seen.find_one({"url": url}) is not None

    def mark_seen(self, url: str):
        try:
            self.seen.insert_one({"url": url, "first_seen": datetime.now(timezone.utc)})
        except errors.DuplicateKeyError:
            pass

    def save_job(self, job: dict) -> bool:
        try:
            self.jobs.insert_one({
                **job,
                "created_at": datetime.now(timezone.utc),
                "sent": False
            })
            self.mark_seen(job["url"])
            return True
        except errors.DuplicateKeyError:
            return False

    def get_unsent_jobs(self) -> List[dict]:
        return list(self.jobs.find({"sent": False}).sort("created_at", -1))

    def mark_sent(self, job_id):
        self.jobs.update_one({"_id": job_id}, {"$set": {"sent": True}})

    def mark_all_sent(self):
        self.jobs.update_many({"sent": False}, {"$set": {"sent": True}})

    def close(self):
        self.client.close()
