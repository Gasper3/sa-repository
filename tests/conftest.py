import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from .models import Base
from .repositories import ArticleRepository

engine = create_engine('postgresql://postgres:postgres@127.0.0.1:5433/sa_repository')
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
global_session = Session()


@pytest.fixture(scope='session')
def create_test_db():
    engine = create_engine('postgresql://postgres:postgres@127.0.0.1:5433/')
    connection = engine.connect()
    connection.execution_options(isolation_level="AUTOCOMMIT")

    connection.execute(text('DROP DATABASE IF EXISTS sa_repository;'))
    connection.execute(text('CREATE DATABASE sa_repository;'))

    yield


@pytest.fixture(scope='session')
def db_engine(create_test_db):
    engine = create_engine('postgresql://postgres:postgres@127.0.0.1:5433/sa_repository')

    with engine.begin() as connection:
        Base.metadata.create_all(bind=connection)

    yield engine
    with engine.begin() as connection:
        Base.metadata.clear()
    engine.dispose()


@pytest.fixture(autouse=True)
def db_session(db_engine):
    ses = global_session
    ses.begin_nested()
    yield ses
    ses.rollback()
    ses.close()


@pytest.fixture()
def repository(db_session):
    return ArticleRepository(db_session)
