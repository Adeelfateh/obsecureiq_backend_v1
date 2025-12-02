import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
from models import Base

# Load environment variables (only if .env file exists)
from dotenv import load_dotenv
if os.path.exists('.env'):
    load_dotenv()
    print("📁 Loaded .env file")
else:
    print("🌐 Using Railway environment variables")

# Database configuration with fallback values
DB_HOST = os.getenv("DB_HOST") or "aws-1-us-west-1.pooler.supabase.com"
DB_PORT = os.getenv("DB_PORT") or "6543"
DB_NAME = os.getenv("DB_NAME") or "postgres"
DB_USER = os.getenv("DB_USER") or "postgres.tgqpsbfwkzdgmynrdvnc"
DB_PASSWORD = os.getenv("DB_PASSWORD") or "admin123"
DB_SSLMODE = os.getenv("DB_SSLMODE") or "require"

print(f"🔗 Connecting to database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
# URL encode password to handle special characters
encoded_password = quote_plus(DB_PASSWORD)

# Build connection string
DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSLMODE}"

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

print(f"✅ Database connection established successfully")



# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
