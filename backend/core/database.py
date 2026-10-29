"""Database engine, async session factory, and base models."""

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from backend.core.config import settings

import sys
from sqlalchemy.pool import NullPool

def _engine_url_and_args():
    """asyncpg does not understand libpq's ?sslmode=... so translate it into connect_args."""
    from sqlalchemy.engine import make_url

    url = make_url(settings.DATABASE_URL)
    connect_args = {}
    sslmode = url.query.get("sslmode")
    if sslmode:
        url = url.difference_update_query(["sslmode", "channel_binding"])
        if sslmode in ("require", "verify-ca", "verify-full"):
            connect_args["ssl"] = "require"
    return url, connect_args


_db_url, _connect_args = _engine_url_and_args()

engine = create_async_engine(
    _db_url,
    connect_args=_connect_args,
    echo=False,
    pool_pre_ping=True,
    poolclass=NullPool if "pytest" in sys.modules else None,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
