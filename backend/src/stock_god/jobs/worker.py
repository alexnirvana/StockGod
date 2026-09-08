import json
import logging
import os
import signal
import time
from datetime import timedelta
from uuid import uuid4
from sqlalchemy import or_, select, and_
from apscheduler.schedulers.background import BackgroundScheduler
from stock_god.db.models import Job, now
from stock_god.db.session import database, transaction, heartbeat_path
from stock_god.research.backtest import run_backtest
from stock_god.adapters.parquet import publish_teaching_snapshot
from stock_god.adapters.vnpy_events import WorkerEvents

logger = logging.getLogger("stock_god.worker")


def heartbeat(engine):
    target = heartbeat_path(engine)
    tmp = target.with_suffix("." + str(uuid4()) + ".tmp")
    tmp.write_text(json.dumps({"timestamp": now().timestamp(), "pid": os.getpid()}))
    os.replace(tmp, target)


def claim(factory):
    with transaction(factory) as s:
        job = s.scalar(select(Job).where(or_(Job.status == "queued", and_(Job.status == "running", Job.lease_until < now()))).order_by(Job.created_at).limit(1).with_for_update(skip_locked=True))
        if not job:
            return None
        if job.attempts >= 3:
            job.status, job.error = "failed", "任务已重试三次，请查看日志后重新创建实验。"
            return None
        job.status, job.attempts = "running", job.attempts + 1
        job.lease_until, job.lease_token = now() + timedelta(seconds=120), str(uuid4())
        return job.id, job.lease_token, job.params


def run_once(factory):
    claimed = claim(factory)
    if not claimed:
        return False
    job_id, token, params = claimed
    try:
        result = run_backtest(params)
        with transaction(factory) as s:
            job = s.scalar(select(Job).where(Job.id == job_id).with_for_update())
            if job.status == "running" and job.lease_token == token:
                job.result, job.status, job.finished_at = result, "completed", now()
                job.lease_until = None
    except Exception as error:
        logger.exception("Backtest job %s failed", job_id)
        with transaction(factory) as s:
            job = s.scalar(select(Job).where(Job.id == job_id).with_for_update())
            if job.lease_token == token:
                job.status, job.error = "failed", str(error)
                job.lease_until = None
    return True


def main():
    logging.basicConfig(level=logging.INFO)
    engine, factory = database()
    publish_teaching_snapshot()
    stop = False
    def shutdown(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(lambda: heartbeat(engine), "interval", seconds=10, id="heartbeat", max_instances=1, coalesce=True)
    scheduler.start()
    heartbeat(engine)
    events = WorkerEvents(lambda: run_once(factory))
    events.start()
    try:
        while not stop:
            events.notify()
            time.sleep(1)
    finally:
        events.stop()
        scheduler.shutdown(wait=False)
        engine.dispose()


if __name__ == "__main__":
    main()
