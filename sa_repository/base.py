from __future__ import annotations

from typing import Any, Generic, Sequence, TypeVar, cast

import more_itertools
import sqlalchemy as sa
from sqlalchemy import ColumnElement
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import DeclarativeBase, Session, joinedload

__all__ = ['BaseRepository']

T = TypeVar('T', bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    """
    Base repository class providing generic CRUD operations for SQLAlchemy models.

    Subclass and set MODEL_CLASS to use::

        class ArticleRepository(BaseRepository[Article]):
            MODEL_CLASS = Article

    All write operations are flushed immediately within a savepoint.
    Exceptions propagate from sqlalchemy.exc.
    """

    BATCH_SIZE: int = 1000

    def __init__(self, session: Session, model_class: type[T]):
        self.session = session
        self.model_class = model_class

    def _convert_params_to_model_fields(self, **params: Any) -> list[ColumnElement]:
        """Convert keyword arguments to a list of SQLAlchemy column equality expressions."""

        result = []
        for name, value in params.items():
            field = getattr(self.model_class, name)
            result.append(cast(ColumnElement, field == value))
        return result

    def _validate_type(self, instances: list[T]) -> None:
        """
        Assert that all instances are of MODEL_CLASS type.

        :raises ValueError: if any instance is not an instance of MODEL_CLASS.
        """

        if not all((isinstance(instance, self.model_class) for instance in instances)):
            raise ValueError(f'Not all models are instance of class {self.model_class.__name__}')

    def _flush_obj(self, obj: T) -> None:
        """Add obj to the session and flush within a savepoint."""

        self.session.add(obj)
        with self.session.begin_nested():
            self.session.flush()

    def get_or_create(self, **params: Any) -> tuple[T, bool]:
        """
        Fetch a single matching record or create one with the given params.

        :returns: (instance, created) — created is True if a new record was inserted.
        :raises MultipleResultsFound: if the lookup matches more than one record.
        :raises IntegrityError: on concurrent insert of the same unique key.
        """

        try:
            return self.get(*self._convert_params_to_model_fields(**params)), False
        except NoResultFound:
            return self.create(**params), True

    def get_query(
        self,
        *where_args: ColumnElement,
        joins: list[Any] | None = None,
        order_by: ColumnElement | None = None,
        joined_loads: tuple[Any, ...] | None = None,
    ) -> sa.Select:
        """
        Build a SELECT statement without executing it.

        :param where_args: Column filter expressions (ANDed together).
        :param joins: List of join targets. Each element is either a mapped class/relationship
                      or a (target, condition) tuple passed to Query.join().
        :param select: Tuple of column expressions for column-level projection. When provided
                       the query returns rows, not model instances — use session.execute() directly.
        :param order_by: A single column expression for ORDER BY.
        :param joined_loads: Tuple of relationship attributes to eagerly load via JOIN.
        :returns: An unexecuted sa.Select statement.
        """

        query = sa.select(self.model_class)
        query = query.where(*where_args)
        if order_by is not None:
            query = query.order_by(order_by)

        if joins:
            for join in joins:
                query = query.join(*join) if isinstance(join, tuple) else query.join(join)

        if joined_loads:
            query = query.options(*[joinedload(j) for j in joined_loads])
        return query

    # read methods
    def get(
        self, *where: ColumnElement, joins: list[Any] | None = None, joined_loads: tuple[Any, ...] | None = None
    ) -> T:
        """
        Fetch exactly one record matching the given filters.

        :param where: Column filter expressions (ANDed together).
        :param joins: See get_query.
        :param joined_loads: See get_query.

        :returns: The matched model instance.

        :raises NoResultFound: if no record matches.
        :raises MultipleResultsFound: if more than one record matches.
        """

        stmt = self.get_query(*where, joins=joins, joined_loads=joined_loads)
        return self.session.scalars(stmt).unique().one()

    def get_or_none(
        self, *where: ColumnElement, joins: list[Any] | None = None, joined_loads: tuple[Any, ...] | None = None
    ) -> T | None:
        """
        Fetch one record matching the given filters, or None if not found.

        :param where: Column filter expressions (ANDed together).
        :param joins: See get_query.
        :param joined_loads: See get_query.
        :returns: The matched model instance, or None.
        :raises MultipleResultsFound: if more than one record matches.
        """

        stmt = self.get_query(*where, joins=joins, joined_loads=joined_loads)
        return self.session.scalars(stmt).unique().one_or_none()

    def find(
        self,
        *where: ColumnElement,
        joins: list[Any] | None = None,
        order_by: ColumnElement | None = None,
        joined_loads: tuple[Any, ...] | None = None,
    ) -> Sequence[T]:
        """
        Fetch all records matching the given filters.

        :param where: Column filter expressions (ANDed together). Omit to return all rows.
        :param joins: See get_query.
        :param order_by: See get_query.
        :param joined_loads: See get_query.
        :returns: Sequence of matched model instances (empty if none found).
        """

        stmt = self.get_query(*where, joins=joins, order_by=order_by, joined_loads=joined_loads)
        return self.session.scalars(stmt).unique().all()

    # write methods
    def create(self, **params: Any) -> T:
        """
        Create and flush a new model instance.

        :param params: Column values passed as keyword arguments to MODEL_CLASS.
        :returns: The newly created and flushed instance.
        :raises TypeError: if any kwarg is not a valid model attribute.
        """

        obj = self.model_class(**params)
        self._flush_obj(obj)
        return obj

    def create_batch(self, instances: list[T]) -> list[T]:
        """
        Add and flush a list of pre-constructed model instances.

        All instances are validated and inserted within a single savepoint. If any flush
        fails the entire batch is rolled back atomically.

        :param instances: List of MODEL_CLASS instances to persist.
        :returns: The same list of instances.
        :raises ValueError: if any instance is not of MODEL_CLASS type.
        """

        self._validate_type(instances)

        with self.session.begin_nested() as savepoint:
            try:
                for chunk in more_itertools.chunked(instances, self.BATCH_SIZE):
                    self.session.add_all(chunk)
                    self.session.flush()
            except Exception as e:
                savepoint.rollback()
                raise e
        return instances

    def create_batch_from_dicts(self, data: list[dict[str, Any]]) -> list[T]:
        """
        Create and flush model instances from a list of attribute dicts.

        All creates are performed within a single savepoint. If any insert fails the
        entire batch is rolled back atomically.

        :param data: List of dicts mapping column names to values.
        :returns: List of newly created and flushed instances.
        """

        instances: list[T] = []
        with self.session.begin_nested() as savepoint:
            try:
                for chunk in more_itertools.chunked(data, self.BATCH_SIZE):
                    result = [self.create(**item) for item in chunk]
                    instances.extend(result)
            except Exception as e:
                savepoint.rollback()
                raise e
        return instances
