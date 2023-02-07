from factory import LazyAttributeSequence, SubFactory
from factory.alchemy import SQLAlchemyModelFactory, SESSION_PERSISTENCE_COMMIT

from .conftest import Session
from .models import Article, Comment


class BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        sqlalchemy_session = Session
        sqlalchemy_session_persistence = SESSION_PERSISTENCE_COMMIT


class ArticleFactory(BaseFactory):
    class Meta:
        model = Article

    title = LazyAttributeSequence(lambda i: f'Article #{i}')


class CommentFactory(BaseFactory):
    class Meta:
        model = Comment

    content = LazyAttributeSequence(lambda i: f'Comment #{i}')
    article = SubFactory(ArticleFactory)
