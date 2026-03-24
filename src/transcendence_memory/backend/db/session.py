from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..settings import BackendSettings


def create_engine_from_settings(settings: BackendSettings):
    return create_engine(settings.database_url, future=True)


def create_session_factory(settings: BackendSettings) -> sessionmaker[Session]:
    engine = create_engine_from_settings(settings)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
