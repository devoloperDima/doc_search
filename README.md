# Document Search

Простой поисковик по текстам документов.

- **FastAPI**: асинхронный HTTP-сервис
- **PostgreSQL** (SQLAlchemy 2 + asyncpg): хранилище документов
- **Elasticsearch 8**: поисковый индекс с русской морфологией (стемминг, стоп-слова)
- **Docker Compose**: весь сервис поднимается одной командой
- **pytest**: функциональные тесты на настоящих PostgreSQL и Elasticsearch

## Структура данных

Таблица `documents` в PostgreSQL:

| поле           | тип         | описание                  |
|----------------|-------------|---------------------------|
| `id`           | `integer`   | уникальный id документа   |
| `rubrics`      | `varchar[]` | массив рубрик             |
| `text`         | `text`      | текст документа           |
| `created_date` | `timestamp` | дата создания документа   |

Индекс `documents` в Elasticsearch: `id` (id из базы) и `text` (текст из базы).

## API

Полная документация в формате OpenAPI лежит в [`docs.json`](docs.json). После запуска
её можно посмотреть в Swagger UI: http://localhost:8000/docs.

| метод    | путь                             | описание |
|----------|----------------------------------|----------|
| `GET`    | `/documents/search?query=<текст>` | ищет запрос по тексту в индексе, берёт первые 20 найденных документов и возвращает их со всеми полями из БД, отсортированными по дате создания (сначала новые) |
| `DELETE` | `/documents/{id}`                | удаляет документ из БД и индекса. Отвечает `204`, если документ удалён, и `404`, если его нет |

Пример:

```bash
curl "http://localhost:8000/documents/search?query=конкурс"
curl -X DELETE http://localhost:8000/documents/1
```

## Запуск в Docker

1. Положите тестовые данные в `data/posts.csv`
   ([ссылка на датасет](https://disk.yandex.ru/d/UYooXd9q2yqTMQ)).
2. Поднимите сервис:

   ```bash
   docker compose up -d --build
   ```

3. Загрузите данные в БД и индекс. Скрипт пересоздаёт таблицу и индекс, поэтому
   его можно запускать повторно:

   ```bash
   docker compose exec app python -m scripts.load_data
   ```

Сервис будет доступен на http://localhost:8000.

Если порт `5432` на хосте занят, скопируйте `.env.example` в `.env` и укажите
свободный порт в `POSTGRES_PORT` и `DATABASE_URL`.

## Тесты

Тесты используют отдельную БД `documents_test` (она создаётся при первом запуске
контейнера PostgreSQL) и отдельный индекс `documents_test`, поэтому основные данные
не затрагиваются.

```bash
docker compose exec app pytest
```

## Локальная разработка

PostgreSQL и Elasticsearch запускаются в Docker, приложение запускается локально:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
docker compose up -d postgres elasticsearch
python -m scripts.load_data data/posts.csv
uvicorn app.main:app --reload
pytest
```

После изменения API обновите `docs.json`:

```bash
python -m scripts.export_openapi
```

## Структура проекта

```
app/
  main.py       приложение FastAPI, подключение к БД и Elasticsearch
  api.py        эндпоинты поиска и удаления
  db.py         модель Document и работа с PostgreSQL
  search.py     работа с индексом Elasticsearch
  schemas.py    схемы ответов
  config.py     настройки из переменных окружения
scripts/
  load_data.py       загрузка CSV в БД и индекс
  export_openapi.py  генерация docs.json
tests/          функциональные тесты
```
