from sa_repository import BaseRepository
from .models import Article


class ArticleRepository(BaseRepository[Article]):
    MODEL_CLASS = Article
