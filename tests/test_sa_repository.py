import pytest

from sa_repository import __version__, BaseRepository
from .factories import ArticleFactory
from .models import Article, Comment
from .repositories import ArticleRepository


def test_version():
    assert __version__ == '0.1.0'


def test_validate_type(db_session):
    repository = ArticleRepository(db_session)
    repository._validate_type(instances=[Article(), Article()])


def test_validate_type__error(db_session):
    repository = ArticleRepository(db_session)

    with pytest.raises(ValueError) as e:
        repository._validate_type(instances=[Article(), Comment()])
    assert e.value.args[0] == f'Not all models are instance of class Article'


def test_registry():
    class NewRepository(BaseRepository[Article]):
        pass
    with pytest.raises(KeyError) as e:
        class NewRepository(BaseRepository[Article]):
            pass
    assert e.value.args[0] == 'Class NewRepository already exists in registry'


class TestReadMethods:
    def test_get(self, db_session):
        article = ArticleFactory()
        repository = ArticleRepository(db_session)

        result = repository.get(Article.id == article.id)
        assert result.title == article.title
