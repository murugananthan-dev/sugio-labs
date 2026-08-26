import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from ..config import settings

logger = logging.getLogger("sugio_labs.db")

# Ensure data directory exists
data_dir = settings.base_dir / "data"
data_dir.mkdir(parents=True, exist_ok=True)

# Database Engine
db_url = settings.database_url
if db_url.startswith("sqlite"):
    # SQLite configuration for local development
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(db_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
