from random import randint

import pytest
from sqlalchemy import exc

from sa_repository import BaseRepository
from .factories import ArticleFactory, CommentFactory
from .models import Article, Comment
from .repositories import ArticleRepository


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
    assert e.value.args[0] == f'Class {NewRepository.__name__} already exists in registry'


class TestReadMethods:
    @pytest.fixture()
    def repository(self, db_session):
        return ArticleRepository(db_session)

    def test_get(self, repository):
        article = ArticleFactory()

        result = repository.get(Article.id == article.id)
        assert result.title == article.title

    def test_get__not_found(self, repository):
        with pytest.raises(exc.NoResultFound):
            repository.get(Article.id == 999)

    def test_get__multiple_results(self, repository):
        ArticleFactory.create_batch(2, title='Some title')

        with pytest.raises(exc.MultipleResultsFound):
            repository.get(Article.title == 'Some title')

    def test_find(self, repository):
        articles = ArticleFactory.create_batch(5, group='python')

        result = repository.find(Article.group == 'python')
        assert len(result) == len(articles)

        ids = [article.id for article in result]
        assert all([article.id in ids for article in articles])

    def test_find__relation(self, repository):
        comment = CommentFactory()
        ArticleFactory.create_batch(5)

        result = repository.find(Comment.article == comment.article, join=Article.comments)
        assert len(result) == 1


class TestGetRepositoryFromModel:
    def test_get_repository_from_model(self, db_session):
        articles_1 = ArticleFactory.create_batch(randint(1, 10), group='group #1')
        articles_2 = ArticleFactory.create_batch(randint(1, 10), group='group #2')

        repository = BaseRepository.get_repository_from_model(db_session, Article)

        result = repository.find(Article.group == 'group #1')
        assert len(result) == len(articles_1)

        result = repository.find(Article.group == 'group #2')
        assert len(result) == len(articles_2)

        comments = CommentFactory.create_batch(randint(1, 10), article=articles_2[0])
        comment_repository = BaseRepository.get_repository_from_model(db_session, Comment)

        result = comment_repository.find(Comment.article == articles_2[0])
        assert len(result) == len(comments)

        result = ArticleRepository(db_session).find(Article.group == 'group #1')
        assert len(result) == len(articles_1)
