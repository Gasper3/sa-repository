from random import randint

import pytest
from sqlalchemy import exc, BinaryExpression

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


class TestRepository:
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

    def test_get_or_create__get(self, repository):
        article = ArticleFactory()

        obj, created = repository.get_or_create(id=article.id)
        assert obj
        assert not created

    def test_get_or_create__multiple_results_error(self, repository):
        ArticleFactory.create_batch(2, group='group#1')

        with pytest.raises(exc.MultipleResultsFound):
            repository.get_or_create(group='group#1')

    def test_get_or_create__create(self, repository):
        obj, created = repository.get_or_create(title='New title')

        assert created
        assert obj.title == 'New title'

        result = repository.get(Article.id == obj.id)
        assert result
        assert result.title == 'New title'

    def test_convert_params_to_model_fields(self, repository):
        expected_result: list[BinaryExpression] = [Article.title == 'new title', Article.group == 'group #1']
        result = repository._convert_params_to_model_fields(title='new title', group='group #1')

        assert len(result) == 2
        assert expected_result[0].compare(result[0])
        assert expected_result[1].compare(result[1])

    def test_convert_params_to_model_fields__field_not_exist(self, repository):
        with pytest.raises(AttributeError):
            repository._convert_params_to_model_fields(bad_field='new title')


class TestWriteMethods:
    def test_create(self, repository):
        article = repository.create(title='title-#1')
        assert article

        result = repository.get(Article.title == 'title-#1')
        assert result

    def test_create_batch(self, repository):
        size = randint(10, BaseRepository.BATCH_SIZE)
        repository.create_batch([Article(title=f'title#{i}', group='batch') for i in range(size)])

        result = repository.find(Article.group == 'batch')
        assert len(result) == size

    def test_create_batch__size_exceeded(self, repository):
        with pytest.raises(ValueError) as e:
            repository.create_batch(
                [Article(title=f'title#{i}', group='batch') for i in range(BaseRepository.BATCH_SIZE + 1)]
            )
        assert e.value.args[0] == 'Batch size exceeded'

    def test_update(self, repository):
        article = ArticleFactory()

        obj = repository.update(article, title='updated')
        assert obj.title == 'updated'

        result = repository.get(Article.id == article.id)
        assert result
        assert result.title == 'updated'
