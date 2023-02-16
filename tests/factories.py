from factory import SubFactory, Sequence
from factory.alchemy import SQLAlchemyModelFactory, SESSION_PERSISTENCE_FLUSH

from .conftest import Session
from .models import Article, Comment


class BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        sqlalchemy_session = Session
        sqlalchemy_session_persistence = SESSION_PERSISTENCE_FLUSH


class ArticleFactory(BaseFactory):
    class Meta:
        model = Article

    title = Sequence(lambda i: f'Article #{i}')


class CommentFactory(BaseFactory):
    class Meta:
        model = Comment

    content = Sequence(lambda i: f'Comment #{i}')
    article = SubFactory(ArticleFactory)
