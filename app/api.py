from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import Document, get_session
from app.schemas import DocumentOut, ErrorOut
from app.search import SearchIndex, get_search_index

router = APIRouter(prefix='/documents', tags=['documents'])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SearchIndexDep = Annotated[SearchIndex, Depends(get_search_index)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get(
    '/search',
    response_model=list[DocumentOut],
    summary='Поиск документов по тексту',
    description=(
        'Ищет запрос по тексту документов в Elasticsearch, берёт первые 20 '
        'найденных документов и возвращает их со всеми полями из БД, '
        'упорядоченными по дате создания (сначала новые).'
    ),
)
async def search_documents(
    session: SessionDep,
    search_index: SearchIndexDep,
    settings: SettingsDep,
    query: Annotated[
        str, Query(min_length=1, description='Произвольный текстовый запрос')
    ],
) -> list[Document]:
    ids = await search_index.search(query, limit=settings.search_limit)
    if not ids:
        return []
    result = await session.scalars(
        select(Document)
        .where(Document.id.in_(ids))
        .order_by(Document.created_date.desc(), Document.id.desc())
    )
    return list(result)


@router.delete(
    '/{document_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Удаление документа',
    description='Удаляет документ из БД и поискового индекса по id.',
    responses={status.HTTP_404_NOT_FOUND: {'model': ErrorOut}},
)
async def delete_document(
    document_id: int,
    session: SessionDep,
    search_index: SearchIndexDep,
) -> Response:
    result = await session.execute(
        delete(Document).where(Document.id == document_id)
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Документ не найден',
        )
    await search_index.delete(document_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
