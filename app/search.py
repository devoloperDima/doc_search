from collections.abc import Iterable

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk
from fastapi import Request

INDEX_SETTINGS = {
    'analysis': {
        'analyzer': {
            'text_ru': {
                'type': 'custom',
                'tokenizer': 'standard',
                'filter': ['lowercase', 'russian_stop', 'russian_stemmer'],
            },
        },
        'filter': {
            'russian_stop': {'type': 'stop', 'stopwords': '_russian_'},
            'russian_stemmer': {'type': 'stemmer', 'language': 'russian'},
        },
    },
}

INDEX_MAPPINGS = {
    'properties': {
        'id': {'type': 'long'},
        'text': {'type': 'text', 'analyzer': 'text_ru'},
    },
}


class SearchIndex:
    """Обёртка над индексом Elasticsearch с документами (id, text)."""

    def __init__(self, client: AsyncElasticsearch, index: str) -> None:
        self.client = client
        self.index = index

    async def create(self, recreate: bool = False) -> None:
        exists = await self.client.indices.exists(index=self.index)
        if exists and recreate:
            await self.client.indices.delete(index=self.index)
            exists = False
        if not exists:
            await self.client.indices.create(
                index=self.index,
                settings=INDEX_SETTINGS,
                mappings=INDEX_MAPPINGS,
            )

    async def add_many(
        self, documents: Iterable[tuple[int, str]], refresh: bool = False
    ) -> None:
        actions = (
            {
                '_index': self.index,
                '_id': doc_id,
                '_source': {'id': doc_id, 'text': text},
            }
            for doc_id, text in documents
        )
        await async_bulk(self.client, actions, refresh=refresh)

    async def search(self, query: str, limit: int) -> list[int]:
        """Возвращает id самых релевантных документов."""
        response = await self.client.search(
            index=self.index,
            query={'match': {'text': query}},
            size=limit,
            source=False,
        )
        return [int(hit['_id']) for hit in response['hits']['hits']]

    async def delete(self, doc_id: int, refresh: bool = False) -> bool:
        try:
            await self.client.delete(
                index=self.index, id=str(doc_id), refresh=refresh
            )
        except NotFoundError:
            return False
        return True


def get_search_index(request: Request) -> SearchIndex:
    return request.app.state.search_index
