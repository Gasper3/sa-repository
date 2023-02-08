from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship


class MyBase:
    id = Column(Integer(), primary_key=True)


Base = declarative_base(cls=MyBase)


class Comment(Base):
    __tablename__ = 'comments'

    content = Column(String(255))

    article_id = Column(Integer(), ForeignKey("articles.id"))
    article = relationship('Article', back_populates='comments')


class Article(Base):
    __tablename__ = 'articles'

    title = Column(String(255))

    comments = relationship('Comment', back_populates='article')
