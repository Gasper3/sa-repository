from sqlalchemy.orm import Session

from sa_repository import BaseRepository

from .models import Article, Comment


class ArticleRepository(BaseRepository[Article]):
    def __init__(self, session: Session):
        super().__init__(session, Article)


class CommentRepository(BaseRepository[Comment]):
    def __init__(self, session: Session):
        super().__init__(session, Comment)
