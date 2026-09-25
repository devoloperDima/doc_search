from http import HTTPStatus

from app.main import app

SEARCH_URL = '/documents/search'


async def search(client, query):
    return await client.get(SEARCH_URL, params={'query': query})


async def test_search_returns_documents_sorted_by_date(client):
    response = await search(client, 'леон')

    assert response.status_code == HTTPStatus.OK
    assert [doc['id'] for doc in response.json()] == [2, 3, 1]


async def test_search_returns_all_db_fields(client):
    response = await search(client, 'борщ')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == [
        {
            'id': 4,
            'rubrics': [],
            'text': 'Рецепт борща со сметаной',
            'created_date': '2021-03-01T08:00:00',
        },
    ]


async def test_search_uses_russian_morphology(client):
    response = await search(client, 'лекарства')

    assert [doc['id'] for doc in response.json()] == [1]


async def test_search_without_matches(client):
    response = await search(client, 'космос')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


async def test_search_limits_results(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), 'search_limit', 2)
    response = await search(client, 'леон')

    assert len(response.json()) == 2


async def test_search_requires_query(client):
    for params in ({}, {'query': ''}):
        response = await client.get(SEARCH_URL, params=params)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_delete_document(client):
    response = await client.delete('/documents/2')

    assert response.status_code == HTTPStatus.NO_CONTENT
    search_response = await search(client, 'леон')
    assert [doc['id'] for doc in search_response.json()] == [3, 1]
    assert not await app.state.search_index.delete(2)


async def test_delete_missing_document(client):
    response = await client.delete('/documents/999')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Документ не найден'}
