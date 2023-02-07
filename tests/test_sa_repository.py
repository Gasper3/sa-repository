import pytest

from sa_repository import __version__
from .models import Article, Comment
from .repositories import ArticleRepository


def test_version():
    assert __version__ == '0.1.0'


def test_validate_type(session):
    repository = ArticleRepository(session)
    repository._validate_type(instances=[Article(), Article()])


def test_validate_type__error(session):
    repository = ArticleRepository(session)

    with pytest.raises(ValueError) as e:
        repository._validate_type(instances=[Article(), Comment()])
