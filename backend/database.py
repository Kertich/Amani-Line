import os
from collections.abc import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# 1. Look for and load the secret key-values sitting inside the .env file
load_dotenv()

# For async, your Supabase connection string must start with postgresql+asyncpg://
# Get this from your Supabase Dashboard -> Project Settings -> Database -> Connection Strings
# 2. Pull the string out securely (and fall back to a dummy string if missing)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:[YOUR-PASSWORD]@[YOUR-SUBDOMAIN].supabase.co:5432/postgres")

# Create the async engine
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=True,
    # 🔌 Add these parameters below to explicitly fix the PgBouncer problem
    connect_args={
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0
    }
    )

# Create an async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    autocommit=False, 
    autoflush=False, 
    expire_on_commit=False
)

# Base class for your database models
class Base(DeclarativeBase):
    pass

# FastAPI Dependency injection function to get db session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
