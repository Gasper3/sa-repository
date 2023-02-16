import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from .models import Base
from .repositories import ArticleRepository

DB_URL = 'sqlite:///./test.db'

Session = scoped_session(sessionmaker())


@pytest.fixture(scope='session')
def db_engine():
    engine = create_engine(DB_URL)

    with engine.begin() as connection:
        Base.metadata.create_all(bind=connection)

    yield engine

    with engine.begin() as connection:
        Base.metadata.drop_all(bind=connection)
    engine.dispose()


@pytest.fixture(scope='session')
def prepare_db(db_engine):
    engine = create_engine(DB_URL)
    Session.configure(bind=engine)
    yield


@pytest.fixture(autouse=True)
def db_session(prepare_db):
    ses = Session()
    ses.begin_nested()
    yield ses
    ses.rollback()
    ses.close()


@pytest.fixture()
def repository(db_session):
    return ArticleRepository(db_session)
