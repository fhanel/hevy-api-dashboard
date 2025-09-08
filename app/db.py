import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.orm import declarative_base

# Single declarative Base
Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

@contextmanager
def get_db() -> Connection:
    """
    Yield a transactional connection. Transaction is committed on success
    and rolled back automatically if an exception escapes.
    """
    with engine.begin() as conn:  # begin() => transactional Connection
        yield conn

def create_all_tables() -> None:
    """
    Import models here (late) so they register on Base, then create tables.
    This avoids circular imports at module import time.
    """
    from . import models  # noqa: F401  (side-effect: registers mappers)
    Base.metadata.create_all(bind=engine)
