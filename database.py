import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
from models import Base

# Load .env only locally (Railway ignores .env)
from dotenv import load_dotenv
load_dotenv()

# Fetch environment variables safely
DB_HOST = os.getenv("DB_HOST") or None
DB_PORT = os.getenv("DB_PORT") or None
DB_NAME = os.getenv("DB_NAME") or None
DB_USER = os.getenv("DB_USER") or None
DB_PASSWORD = os.getenv("DB_PASSWORD") or None
DB_SSLMODE = os.getenv("DB_SSLMODE") or "require"

# Check for missing required variables (prevents silent failures)
required_vars = {
    "DB_HOST": DB_HOST,
    "DB_PORT": DB_PORT,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
}

missing = [key for key, value in required_vars.items() if not value]
if missing:
    raise ValueError(f"❌ Missing required environment variables: {missing}")

# Encode username and password safely
DB_USER_SAFE = quote_plus(str(DB_USER))
DB_PASSWORD_SAFE = quote_plus(str(DB_PASSWORD))

# Build connection URL
DATABASE_URL = (
    f"postgresql://{DB_USER_SAFE}:{DB_PASSWORD_SAFE}@{DB_HOST}:{DB_PORT}/"
    f"{DB_NAME}?sslmode={DB_SSLMODE}"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(bind=engine)

# Initialize tables
def create_tables():
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

# DB Session Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
