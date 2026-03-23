from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./investment_advisory.db")
    risk_free_rate: float = float(os.getenv("RISK_FREE_RATE", "0.045"))
    rebalance_threshold: float = float(os.getenv("REBALANCE_THRESHOLD", "0.05"))
    yfinance_cache_days: int = int(os.getenv("YFINANCE_CACHE_DAYS", "7"))
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    upload_folder: str = os.getenv("UPLOAD_FOLDER", "backend/uploads")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

# Database setup - handle both PostgreSQL and SQLite
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}

# SQLite doesn't support pool settings
if settings.database_url.startswith("sqlite"):
    engine = create_engine(settings.database_url, **engine_kwargs)
else:
    engine = create_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=10,
        **engine_kwargs
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

def get_db():
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
