import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from jobsearch.db.models import Base
from jobsearch.db.utils import get_db_logger

# Set up logger
logger = get_db_logger(__name__)

# Create database directory if it doesn't exist
DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
)
os.makedirs(DB_DIR, exist_ok=True)

# Database configuration
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'jobsearch.db')}"
logger.info(f"Using database: {SQLALCHEMY_DATABASE_URL}")

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
)

session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create all tables
def init_db():
    logger.info("Initializing database tables")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


if __name__ == "__main__":
    init_db()
