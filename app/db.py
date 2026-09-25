from collections.abc import AsyncIterator
from datetime import datetime

from fastapi import Request
from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = 'documents'

    id: Mapped[int] = mapped_column(primary_key=True)
    rubrics: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_tables(engine: AsyncEngine, drop: bool = False) -> None:
    async with engine.begin() as conn:
        if drop:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session
