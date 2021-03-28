import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from tests.models import Base
from tests.factories import patch_factories_session
from tests.filters import patch_filters_session


@pytest.fixture(scope="session")
def engine():
    _engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(_engine)
    return _engine


@pytest.fixture(scope="function", autouse=True)
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = scoped_session(sessionmaker(bind=connection))
    patch_factories_session(session)
    patch_filters_session(session)
    yield session
    session.remove()
    transaction.rollback()
    connection.close()
