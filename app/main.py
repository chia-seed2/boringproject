from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine
from app.jobs.daily_scan import run_daily_scan
from app.routes import compliance, export, price_snapshots, products, scan, stores

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()

    scheduler.add_job(
        run_daily_scan,
        trigger="interval",
        days=1,
        id="daily_scan",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(days=1),
    )

    yield
    scheduler.shutdown()


Base.metadata.create_all(bind=engine)

app = FastAPI(lifespan=lifespan)

# CORS (keep wide open for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(export.router)
app.include_router(stores.router)
app.include_router(products.router)
app.include_router(price_snapshots.router)
app.include_router(scan.router)
app.include_router(compliance.router)


# Core endpoints
@app.get("/")
def root():
    return {"message": "ScanGuard backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/jobs/run-daily-scan-now")
def run_daily_scan_now():
    result = run_daily_scan()
    return {
        "status": "daily scan completed",
        "summary": result,
    }


# Debug + timer endpoints
@app.get("/jobs/debug")
def debug_jobs():
    jobs = scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        }
        for job in jobs
    ]


@app.get("/jobs/next-scan")
def get_next_scan():
    job = scheduler.get_job("daily_scan")
    next_run = job.next_run_time if job else None

    return {
        "job_id": "daily_scan",
        "next_run_time": next_run.isoformat() if next_run else None,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }
