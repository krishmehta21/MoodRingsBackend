from fastapi import FastAPI
import models
from database import engine
from routers import auth, logs, dashboard, risk, suggestions, insights, calendar
from fastapi.middleware.cors import CORSMiddleware

try:
    models.Base.metadata.create_all(bind=engine)
    print("Database connected")
except Exception as e:
    print("Database connection failed:", e)

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

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def read_root():
    return {"message": "MoodRings Backend API is strictly running!"}
