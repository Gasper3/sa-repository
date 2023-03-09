from __future__ import annotations

import typing as t

from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)


class Article(Base):
    __tablename__ = 'articles'

    title: Mapped[str] = mapped_column(unique=True)
    group: Mapped[t.Optional[str]]

    comments: Mapped[list[Comment]] = relationship(back_populates='article')
    categories: Mapped[list[Category]] = relationship(secondary='article_to_category', back_populates='articles')


class Comment(Base):
    __tablename__ = 'comments'

    content: Mapped[str]
    article_id = mapped_column(ForeignKey('articles.id'))

    article: Mapped[Article] = relationship(back_populates='comments')


class Category(Base):
    __tablename__ = 'categories'

    name: Mapped[str]

    articles: Mapped[list[Article]] = relationship(secondary='article_to_category', back_populates='categories')


class ArticleToCategory(Base):
    __tablename__ = 'article_to_category'

    article_id: Mapped[int] = mapped_column(ForeignKey('articles.id'))
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'))

    article: Mapped[Article] = relationship()
    category: Mapped[Category] = relationship()
