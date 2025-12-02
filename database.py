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

# Database configuration
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")

# Debug: Print available environment variables (without sensitive data)
print(f"Debug - DB_HOST: {DB_HOST}")
print(f"Debug - DB_PORT: {DB_PORT}")
print(f"Debug - DB_NAME: {DB_NAME}")
print(f"Debug - DB_USER: {DB_USER}")
print(f"Debug - DB_PASSWORD: {'***' if DB_PASSWORD else None}")

# Validate required environment variables
required_vars = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print(f"❌ Missing required environment variables: {missing}")
    print("Please check your Railway environment variables configuration.")
    raise ValueError(f"Missing required environment variables: {missing}")
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

print(f"✅ Database connection configured for: {DB_HOST}:{DB_PORT}/{DB_NAME}")



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
