from sa_repository import BaseRepository
from .models import Article, Comment


class ArticleRepository(BaseRepository[Article]):
    MODEL_CLASS = Article


class CommentRepository(BaseRepository[Comment]):
    MODEL_CLASS = Comment
