from __future__ import annotations

from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship, Mapped


class MyBase:
    id = Column(Integer(), primary_key=True)


Base = declarative_base(cls=MyBase)


class Comment(Base):
    __tablename__ = 'comments'

    content = Column(String(255))

    article_id = Column(Integer(), ForeignKey("articles.id"))
    article = relationship('Article', back_populates='comments')


article_to_category = Table(
    'article_to_category',
    Base.metadata,
    Column('article_id', ForeignKey('articles.id'), primary_key=True),
    Column('category_id', ForeignKey('categories.id'), primary_key=True),
)


class Article(Base):
    __tablename__ = 'articles'

    title = Column(String(255), unique=True)
    group = Column(String(255), nullable=True)

    comments = relationship('Comment', back_populates='article')
    categories: Mapped[list[Category]] = relationship(secondary=article_to_category, back_populates='articles')


class Category(Base):
    __tablename__ = 'categories'

    name = Column(String(255))
    articles: Mapped[list[Article]] = relationship(secondary=article_to_category, back_populates='categories')
