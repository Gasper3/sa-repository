import contextlib

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import Base
from .repositories import ArticleRepository, CommentRepository

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
    Session.configure(bind=db_engine)
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


@pytest.fixture()
def c_repository(db_session):
    return CommentRepository(db_session)


@contextlib.contextmanager
def count_queries(conn):
    queries = []
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(conn, "before_cursor_execute", before_cursor_execute)
    try:
        yield queries
    finally:
        event.remove(conn, "before_cursor_execute", before_cursor_execute)
