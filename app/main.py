from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine
from app.jobs.daily_scan import run_daily_scan
from app.routes import compliance, export, price_snapshots, products, scan, stores
from datetime import datetime, timezone
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        run_daily_scan,
        "interval",
        days=1,
        id="daily_scan",
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown()


Base.metadata.create_all(bind=engine)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(export.router)
app.include_router(stores.router)
app.include_router(products.router)
app.include_router(price_snapshots.router)
app.include_router(scan.router)
app.include_router(compliance.router)

@app.get("/jobs/next-scan")
def get_next_scan():
    job = scheduler.get_job("daily_scan")
    next_run = job.next_run_time if job else None

    return {
        "job_id": "daily_scan",
        "next_run_time": next_run.astimezone(timezone.utc).isoformat() if next_run else None,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }
    
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
