# app/api.py

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import json
import asyncio

from app.decision_engine import DecisionEngine
from app.pipeline import Pipeline
from app.job_store import create_job, complete_job, fail_job, get_job
from app.paths import RESULTS_DIR

app = FastAPI(title="Vision Trace OSINT Engine", version="7.0")

# Static mount
app.mount("/data", StaticFiles(directory="data"), name="data")


# -------------------------
# REQUEST MODEL
# -------------------------

class AnalyzeRequest(BaseModel):
    instagram: str | None = None
    twitter: str | None = None


# -------------------------
# ANALYZE
# -------------------------

@app.post("/analyze")
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):

    instagram = request.instagram
    twitter = request.twitter

    if not instagram and not twitter:
        raise HTTPException(status_code=400, detail="No target provided")

    engine = DecisionEngine(instagram, twitter)
    plan = engine.build_plan()
    pipeline = Pipeline(instagram, twitter)

    job_id = create_job()

    def run_pipeline():
        try:
            asyncio.run(pipeline.execute(plan))

            complete_job(job_id, {
                "instagram": instagram,
                "twitter": twitter
            })

        except Exception as e:
            fail_job(job_id, str(e))

    background_tasks.add_task(run_pipeline)

    return {"job_id": job_id}


# -------------------------
# JOB STATUS
# -------------------------

@app.get("/status/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# -------------------------
# FINAL REPORT
# -------------------------

@app.get("/report/{target}")
def get_report(target: str):

    report_path = RESULTS_DIR / target / "final_report.txt"

    if not report_path.exists():
        twitter_only = RESULTS_DIR / f"twitter_only_{target}" / "final_report.txt"
        if twitter_only.exists():
            report_path = twitter_only
        else:
            raise HTTPException(status_code=404, detail="Final report not found")

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {"report": content}


# -------------------------
# OWNER (INSTAGRAM)
# -------------------------

@app.get("/owner/{target}")
def get_owner(target: str):

    owner_path = Path("data/responses") / target / "owner_detection.json"
    image_dir = Path("data/images/instagram") / target

    if not owner_path.exists():
        raise HTTPException(status_code=404, detail="Owner detection not found")

    with open(owner_path, "r", encoding="utf-8") as f:
        owner_data = json.load(f)

    images = []
    if image_dir.exists():
        for img in image_dir.rglob("*"):
            if img.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                web_path = "/data/" + str(img.relative_to("data"))
                images.append(web_path)

    return {
        "images": images,
        "owner_detection": owner_data
    }


# -------------------------
# TWITTER ANALYSIS
# -------------------------

@app.get("/twitter/{target}")
def get_twitter(target: str):

    twitter_path = Path("data/responses") / target / "twitter_analysis.json"

    if not twitter_path.exists():
        twitter_path = Path("data/responses") / f"twitter_only_{target}" / "tweet_analysis.json"

    if not twitter_path.exists():
        raise HTTPException(status_code=404, detail="Twitter analysis not found")

    with open(twitter_path, "r", encoding="utf-8") as f:
        twitter_data = json.load(f)

    return twitter_data


# -------------------------
# FRONTEND (LAST)
# -------------------------

app.mount("/", StaticFiles(directory="app/static", html=True), name="frontend")
