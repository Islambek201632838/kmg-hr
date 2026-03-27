from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Remote DB — read-only (организаторы)
remote_engine = create_async_engine(
    settings.remote_db_url,
    echo=False,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)
RemoteSession = async_sessionmaker(remote_engine, class_=AsyncSession, expire_on_commit=False)

# Local DB — read-write (AI results)
local_engine = create_async_engine(
    settings.local_db_url,
    echo=False,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)
LocalSession = async_sessionmaker(local_engine, class_=AsyncSession, expire_on_commit=False)


class RemoteBase(DeclarativeBase):
    pass


class LocalBase(DeclarativeBase):
    pass


async def get_remote_session():
    async with RemoteSession() as session:
        yield session


async def get_local_session():
    async with LocalSession() as session:
        yield session


async def init_local_db():
    async with local_engine.begin() as conn:
        await conn.run_sync(LocalBase.metadata.create_all)
