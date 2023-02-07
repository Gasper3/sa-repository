import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

engine = create_engine('postgresql://postgres:postgres@127.0.0.1:5433/sa_repository')
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope='session')
def create_test_db():
    engine = create_engine('postgresql://postgres:postgres@127.0.0.1:5433/')
    connection = engine.connect()
    connection.execution_options(isolation_level="AUTOCOMMIT")

    connection.execute(f'DROP DATABASE IF EXISTS sa_repository;')
    connection.execute(f'CREATE DATABASE sa_repository;')

    try:
        yield
    finally:
        connection.execute(f'DROP DATABASE sa_repository;')


@pytest.fixture(scope='session')
def db_engine(create_test_db):
    engine = create_engine('postgresql://postgres:postgres@127.0.0.1:5433/sa_repository')

    with engine.begin() as connection:
        connection.run_callable(Base.metadata.create_all)

    yield engine
    engine.dispose()


@pytest.fixture(scope='session')
def setup_database(db_engine):
    # db.SessionTest.configure(bind=db_engine)
    yield


@pytest.fixture(autouse=True)
def db_session(setup_database):
    ses = Session()
    ses.begin_nested()
    yield ses
    ses.rollback()
    ses.close()
