from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

db_url = settings.DATABASE_URL

# Handle Neon/Render connection strings: convert legacy postgres:// to postgresql://
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {}
engine_kwargs = {
    # pool_pre_ping ensures connections recover seamlessly when Neon serverless compute sleeps
    "pool_pre_ping": True,
    "echo": (settings.ENVIRONMENT == "development" and settings.LOG_LEVEL == "DEBUG"),
}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # Recycle connections every 5 minutes to prevent stale socket errors with Neon poolers
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
