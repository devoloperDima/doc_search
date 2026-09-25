"""Функциональные тесты работают с настоящими PostgreSQL и Elasticsearch.

Используются отдельная тестовая БД и отдельный индекс, чтобы не затрагивать
основные данные. Их адреса задаются переменными TEST_DATABASE_URL и
TEST_ELASTICSEARCH_INDEX; по умолчанию берётся DATABASE_URL с базой
documents_test.
"""
import os

from sqlalchemy.engine import make_url

from app.config import Settings, get_settings

os.environ['DATABASE_URL'] = os.getenv('TEST_DATABASE_URL') or (
    make_url(Settings().database_url)
    .set(database='documents_test')
    .render_as_string(hide_password=False)
)
os.environ['ELASTICSEARCH_INDEX'] = os.getenv(
    'TEST_ELASTICSEARCH_INDEX', 'documents_test'
)
get_settings.cache_clear()

from datetime import datetime  # noqa: E402

import pytest  # noqa: E402
from asgi_lifespan import LifespanManager  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from app.db import Document  # noqa: E402
from app.main import app  # noqa: E402

DOCUMENTS = [
    Document(
        id=1,
        rubrics=['VK-1'],
        text='Новый боец Леон получил тайное лекарство',
        created_date=datetime(2019, 7, 25, 12, 0),
    ),
    Document(
        id=2,
        rubrics=['VK-1', 'VK-2'],
        text='Конкурс! Разыгрываем леона и три тысячи гемов',
        created_date=datetime(2020, 1, 10, 9, 30),
    ),
    Document(
        id=3,
        rubrics=['VK-3'],
        text='Обновление баланса: Леон стал слабее',
        created_date=datetime(2019, 12, 31, 23, 59),
    ),
    Document(
        id=4,
        rubrics=[],
        text='Рецепт борща со сметаной',
        created_date=datetime(2021, 3, 1, 8, 0),
    ),
]


@pytest.fixture
async def client():
    async with LifespanManager(app):
        search_index = app.state.search_index
        await search_index.create(recreate=True)
        async with app.state.session_factory() as session:
            await session.execute(delete(Document))
            session.add_all(
                Document(
                    id=doc.id,
                    rubrics=doc.rubrics,
                    text=doc.text,
                    created_date=doc.created_date,
                )
                for doc in DOCUMENTS
            )
            await session.commit()
        await search_index.add_many(
            ((doc.id, doc.text) for doc in DOCUMENTS), refresh=True
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url='http://test'
        ) as async_client:
            yield async_client
