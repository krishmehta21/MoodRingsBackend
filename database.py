from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/moodrings")

# Strip pgbouncer param if present — invalid for psycopg2
clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")

engine = create_engine(
    clean_url,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"sslmode": "prefer"}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()