# app/job_store.py

from uuid import uuid4
from datetime import datetime

JOBS = {}

def create_job():
    job_id = str(uuid4())
    JOBS[job_id] = {
        "status": "running",
        "created_at": datetime.utcnow().isoformat(),
        "result": None,
        "error": None
    }
    return job_id

def complete_job(job_id, result=None):
    JOBS[job_id]["status"] = "completed"
    JOBS[job_id]["result"] = result

def fail_job(job_id, error):
    JOBS[job_id]["status"] = "failed"
    JOBS[job_id]["error"] = str(error)

def get_job(job_id):
    return JOBS.get(job_id)
