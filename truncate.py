from database import engine
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE users CASCADE"))
print("✅ Users table truncated!")
