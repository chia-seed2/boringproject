from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.db import Base, engine
from app.jobs.daily_scan import run_daily_scan
from app.routes import stores, products, price_snapshots, scan, compliance, export

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
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(export.router)
app.include_router(stores.router)
app.include_router(products.router)
app.include_router(price_snapshots.router)
app.include_router(scan.router)
app.include_router(compliance.router)


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
