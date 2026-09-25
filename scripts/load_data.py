"""Загружает документы из CSV в PostgreSQL и Elasticsearch.

Таблица и индекс пересоздаются, поэтому скрипт можно запускать повторно.

    python -m scripts.load_data data/posts.csv
"""
import argparse
import ast
import asyncio
import csv
from datetime import datetime
from pathlib import Path

from elasticsearch import AsyncElasticsearch

from app.config import get_settings
from app.db import Document, create_engine, create_session_factory, create_tables
from app.search import SearchIndex


def read_documents(path: Path) -> list[Document]:
    with path.open(encoding='utf-8', newline='') as file:
        return [
            Document(
                id=doc_id,
                rubrics=ast.literal_eval(row['rubrics']),
                text=row['text'],
                created_date=datetime.fromisoformat(row['created_date']),
            )
            for doc_id, row in enumerate(csv.DictReader(file), start=1)
        ]


async def load(path: Path) -> None:
    settings = get_settings()
    documents = read_documents(path)

    engine = create_engine(settings.database_url)
    es_client = AsyncElasticsearch(settings.elasticsearch_url)
    search_index = SearchIndex(es_client, settings.elasticsearch_index)
    try:
        await create_tables(engine, drop=True)
        async with create_session_factory(engine)() as session:
            session.add_all(documents)
            await session.commit()

        await search_index.create(recreate=True)
        await search_index.add_many(
            ((doc.id, doc.text) for doc in documents), refresh=True
        )
    finally:
        await es_client.close()
        await engine.dispose()
    print(f'Загружено документов: {len(documents)}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'csv_path', type=Path, nargs='?', default=Path('data/posts.csv')
    )
    asyncio.run(load(parser.parse_args().csv_path))


if __name__ == '__main__':
    main()
