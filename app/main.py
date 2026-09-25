from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI

from app.api import router
from app.config import get_settings
from app.db import create_engine, create_session_factory, create_tables
from app.search import SearchIndex


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    es_client = AsyncElasticsearch(settings.elasticsearch_url)
    search_index = SearchIndex(es_client, settings.elasticsearch_index)

    await create_tables(engine)
    await search_index.create()

    app.state.session_factory = create_session_factory(engine)
    app.state.search_index = search_index
    try:
        yield
    finally:
        await es_client.close()
        await engine.dispose()


app = FastAPI(
    title='Document Search',
    description='Простой поисковик по текстам документов.',
    version='1.0.0',
    lifespan=lifespan,
)
app.include_router(router)
