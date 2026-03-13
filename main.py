from fastapi import FastAPI
import models
from database import engine
from routers import auth, logs, dashboard, risk, suggestions, insights, calendar, nudges
from fastapi.middleware.cors import CORSMiddleware

# Removed create_all to speed up startup. Handled by migrations.

app = FastAPI(title="MoodRings API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(logs.router)
app.include_router(dashboard.router)
app.include_router(risk.router)
app.include_router(suggestions.router)
app.include_router(insights.router)
app.include_router(calendar.router)
app.include_router(nudges.router)

@app.get("/health")
async def health_check():
    return {"ok": True}

@app.get("/")
def read_root():
    return {"message": "MoodRings Backend API is strictly running!"}

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx, os, asyncio
from services.reminders import check_and_send_reminders
from database import SessionLocal

scheduler = AsyncIOScheduler()

async def ping_self():
    app_url = os.getenv("APP_URL", "")
    if not app_url:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.get(f"{app_url}/health")
    except Exception:
        pass  # Silent — keep-alive failure must never crash anything

def run_reminders():
    db = SessionLocal()
    try:
        check_and_send_reminders(db)
    finally:
        db.close()

@app.on_event("startup")
async def start_keep_alive():
    if os.getenv("ENVIRONMENT") == "production":
        scheduler.add_job(ping_self, "interval", minutes=10)
        # Check reminders every hour
        scheduler.add_job(run_reminders, "interval", hours=1)
        scheduler.start()

@app.on_event("shutdown")
async def stop_keep_alive():
    if scheduler.running:
        scheduler.shutdown()
