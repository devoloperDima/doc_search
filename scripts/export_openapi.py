"""Сохраняет OpenAPI-схему сервиса в docs.json."""
import json
from pathlib import Path

from app.main import app

DOCS_PATH = Path(__file__).resolve().parent.parent / 'docs.json'


def main() -> None:
    DOCS_PATH.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    print(f'OpenAPI-схема сохранена в {DOCS_PATH.name}')


if __name__ == '__main__':
    main()
