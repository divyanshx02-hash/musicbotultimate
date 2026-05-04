from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from loguru import logger

from config import MONGO_DB_URI


async def setup_scheduler(db=None) -> AsyncIOScheduler:
    jobstores = {}
    if MONGO_DB_URI:
        try:
            from pymongo import MongoClient
            client = MongoClient(MONGO_DB_URI)
            jobstores["default"] = MongoDBJobStore(database="musicbot", collection="apscheduler_jobs", client=client)
            logger.info("APScheduler using MongoDB jobstore")
        except Exception as e:
            logger.warning(f"MongoDB jobstore failed, using memory: {e}")

    executors = {"default": AsyncIOExecutor()}
    job_defaults = {"coalesce": True, "max_instances": 1}

    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone="UTC",
    )
    return scheduler
