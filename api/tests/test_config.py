"""Configuration tests — specifically the production DATABASE_URL normaliser."""

from __future__ import annotations

from app.core.config import Settings


def test_railway_postgresql_gets_psycopg_driver():
    s = Settings(database_url="postgresql://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_heroku_style_postgres_scheme_is_upgraded():
    s = Settings(database_url="postgres://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_explicit_driver_is_left_alone():
    url = "postgresql+psycopg://u:p@host:5432/db"
    assert Settings(database_url=url).database_url == url


def test_sqlite_default_is_untouched():
    s = Settings(database_url="sqlite:///./test.db")
    assert s.database_url == "sqlite:///./test.db"
    assert s.is_sqlite is True
