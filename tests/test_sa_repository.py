from random import randint

import more_itertools
import pytest
from sqlalchemy import BinaryExpression, exc

from sa_repository import BaseRepository

from .conftest import count_queries
from .factories import ArticleFactory, CategoryFactory, CommentFactory
from .models import Article, Category, Comment
from .repositories import ArticleRepository, CommentRepository


def test_registry(repository):
    with pytest.raises(KeyError) as e:

        class NewRepository(BaseRepository[Article]):
            MODEL_CLASS = Article

    assert e.value.args[0] == f'Repository for model Article already exists in registry'


class TestRepository:
    def test_validate_type(self, repository):
        repository._validate_type(instances=[Article(), Article()])

    def test_validate_type__error(self, repository):
        with pytest.raises(ValueError) as e:
            repository._validate_type(instances=[Article(), Comment()])
        assert e.value.args[0] == f'Not all models are instance of class Article'

    def test_validate_type__batch_exceeded(self, repository):
        with pytest.raises(ValueError) as e:
            repository._validate_type(instances=ArticleFactory.create_batch(BaseRepository.BATCH_SIZE + 1))
        assert e.value.args[0] == f'Batch size exceeded'

    def test_get_repository_from_model(self, db_session):
        articles_1 = ArticleFactory.create_batch(randint(1, 10), group='group #1')
        articles_2 = ArticleFactory.create_batch(randint(1, 10), group='group #2')

        repository = BaseRepository.get_repository_from_model(db_session, Article)
        assert repository.__class__ == ArticleRepository

        result = repository.find(Article.group == 'group #1')
        assert len(result) == len(articles_1)

        result = repository.find(Article.group == 'group #2')
        assert len(result) == len(articles_2)

        comments = CommentFactory.create_batch(randint(1, 10), article=articles_2[0])
        comment_repository = BaseRepository.get_repository_from_model(db_session, Comment)
        assert comment_repository.__class__ == CommentRepository

        result = comment_repository.find(Comment.article == articles_2[0])
        assert len(result) == len(comments)

        result = ArticleRepository(db_session).find(Article.group == 'group #1')
        assert len(result) == len(articles_1)

    def test_get_repository_from_model__new_repository(self, db_session):
        rep = BaseRepository.get_repository_from_model(db_session, Category)
        assert rep.__class__ == BaseRepository

    def test_get_or_create__get(self, repository):
        article = ArticleFactory()

        obj, created = repository.get_or_create(title=article.title)
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

    def test_get_or_create__unique_field_error(self, repository):
        ArticleFactory(title='unique-title')
        with pytest.raises(exc.IntegrityError):
            repository.get_or_create(title='unique-title', group='python')

    def test_get_or_create__unique_field(self, repository):
        article = ArticleFactory(title='unique-title', group='python')
        obj, created = repository.get_or_create(title='unique-title', group='python')

        assert not created
        assert article == obj

    def test_convert_params_to_model_fields(self, repository):
        expected_result: list[BinaryExpression] = [Article.title == 'new title', Article.group == 'group #1']
        result = repository._convert_params_to_model_fields(title='new title', group='group #1')

        assert len(result) == 2
        assert expected_result[0].compare(result[0])
        assert expected_result[1].compare(result[1])

    def test_convert_params_to_model_fields__field_not_exist(self, repository):
        with pytest.raises(AttributeError):
            repository._convert_params_to_model_fields(bad_field='new title')


@pytest.mark.read
class TestReadMethods:
    def test_get(self, repository):
        article = ArticleFactory()

        result = repository.get(Article.id == article.id)
        assert result.title == article.title

    def test_get__not_found(self, repository):
        with pytest.raises(exc.NoResultFound):
            repository.get(Article.id == 999)

    def test_get__multiple_results(self, repository):
        ArticleFactory.create_batch(2, group='group#1')

        with pytest.raises(exc.MultipleResultsFound):
            repository.get(Article.group == 'group#1')

    def test_get_or_none(self, repository):
        article = ArticleFactory()

        db_article = repository.get_or_none(Article.title == article.title)
        assert db_article == article

    def test_get_or_none__miltiple_results(self, repository):
        ArticleFactory.create_batch(2, group='group#1')

        with pytest.raises(exc.MultipleResultsFound):
            repository.get_or_none(Article.group == 'group#1')

    def test_find(self, repository):
        articles = ArticleFactory.create_batch(5, group='python')

        result = repository.find(Article.group == 'python')
        assert len(result) == len(articles)

        ids = [article.id for article in result]
        assert all([article.id in ids for article in articles])

    def test_find__relation(self, repository):
        comment = CommentFactory()
        ArticleFactory.create_batch(5)

        result = repository.find(Comment.article == comment.article, joins=[Article.comments])
        assert len(result) == 1

    def test_find__order(self, repository):
        articles = ArticleFactory.create_batch(5, group='order')

        result = repository.find(Article.group == 'order', order_by=Article.title.desc())
        assert result[0].title == more_itertools.last(articles).title

    def test_m2m__get_relation(self, repository):
        category = CategoryFactory()
        article = ArticleFactory(categories=[category])
        db_article = repository.get(Article.id == article.id)

        assert db_article
        assert db_article.categories == [category]

    def test_get_query__select_columns(self, repository: ArticleRepository):
        article = ArticleFactory(group='group-1')
        ArticleFactory(group='group-2')

        query = repository.get_query(Article.id == article.id, select=(Article.id, Article.group))
        result = repository.session.execute(query).all()

        assert len(result) == 1
        assert result[0] == (1, 'group-1')

    @pytest.mark.parametrize('func', ('get', 'get_or_none', 'find'))
    def test_joined_loads(self, repository: ArticleRepository, db_session, func):
        article = ArticleFactory()
        comments = CommentFactory.create_batch(randint(1, 10), article=article)

        function = getattr(repository, func)

        with count_queries(db_session.connection()) as queries:
            db_article = function(Article.id == article.id, joined_loads=(Article.comments,))
            if func == 'find':
                db_article = more_itertools.first(db_article)
            assert len(db_article.comments) == len(comments)
        assert len(queries) == 1

    @pytest.mark.parametrize('func', ('get', 'get_or_none', 'find'))
    def test_joined_loads__without_joined(self, repository: ArticleRepository, db_session, func):
        article = ArticleFactory()
        comments = CommentFactory.create_batch(randint(1, 10), article=article)

        function = getattr(repository, func)

        with count_queries(db_session.connection()) as queries:
            db_article = function(Article.id == article.id)
            if func == 'find':
                db_article = more_itertools.first(db_article)
            assert len(db_article.comments) == len(comments)
        assert len(queries) == 2


@pytest.mark.write
class TestWriteMethods:
    def test_create(self, repository):
        article = repository.create(title='title-#1')
        assert article

        result = repository.get(Article.title == 'title-#1')
        assert result

    def test_create__invalid_fields(self, repository):
        with pytest.raises(TypeError):
            repository.create(invalid_field='val')

    @pytest.mark.parametrize('size', (randint(10, BaseRepository.BATCH_SIZE), BaseRepository.BATCH_SIZE * 2))
    def test_create_batch(self, repository, size):
        repository.create_batch([Article(title=f'title#{i}', group='batch') for i in range(size)])

        result = repository.find(Article.group == 'batch')
        assert len(result) == size

    @pytest.mark.parametrize('size', (randint(10, BaseRepository.BATCH_SIZE), BaseRepository.BATCH_SIZE * 2))
    def test_create_batch_from_dicts(self, repository, size):
        data = [{'title': f'Article #{i}', 'group': 'batch-dicts'} for i in range(size)]
        instances = repository.create_batch_from_dicts(data)

        assert len(instances) == size
        assert all([isinstance(item, repository.MODEL_CLASS) for item in instances])

    def test_m2m__create(self, repository):
        category = CategoryFactory()
        article = repository.create(categories=[category], title='Some title')

        db_article = repository.get(Article.id == article.id)
        assert db_article
        assert db_article.categories == [category]
