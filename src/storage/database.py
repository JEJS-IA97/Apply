from datetime import datetime, timezone
from typing import List, Optional
from pymongo import MongoClient, errors


class JobDatabase:
    def __init__(self, uri: Optional[str], db_name: str):
        self._available = uri is not None and "user:pass" not in uri
        if self._available:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[db_name]
            self.jobs = self.db["jobs"]
            self.seen = self.db["seen_urls"]

    def is_connected(self) -> bool:
        if not self._available or not hasattr(self, "client"):
            return False
        try:
            self.client.admin.command("ping")
            return True
        except errors.ConnectionFailure:
            return False

    def is_duplicate(self, url: str) -> bool:
        if not hasattr(self, "seen"):
            return False
        return self.seen.find_one({"url": url}) is not None

    def mark_seen(self, url: str):
        if not hasattr(self, "seen"):
            return
        try:
            self.seen.insert_one({"url": url, "first_seen": datetime.now(timezone.utc)})
        except errors.DuplicateKeyError:
            pass

    def save_job(self, job: dict) -> bool:
        if not hasattr(self, "jobs"):
            return False
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
        if not hasattr(self, "jobs"):
            return []
        return list(self.jobs.find({"sent": False}).sort("created_at", -1))

    def mark_sent(self, job_id):
        if not hasattr(self, "jobs"):
            return
        self.jobs.update_one({"_id": job_id}, {"$set": {"sent": True}})

    def mark_all_sent(self):
        if not hasattr(self, "jobs"):
            return
        self.jobs.update_many({"sent": False}, {"$set": {"sent": True}})

    def close(self):
        if hasattr(self, "client"):
            self.client.close()
