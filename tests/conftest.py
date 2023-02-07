import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def session():
    yield Session()
