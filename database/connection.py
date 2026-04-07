from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """Create all tables if they don't exist yet."""
    from database import models  # noqa: F401 — ensures models are registered
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created (or already exist).")
