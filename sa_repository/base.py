import typing as t

import more_itertools
import sqlalchemy as sa
from sqlalchemy import ColumnElement
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, DeclarativeBase

__all__ = ['BaseRepository']

T = t.TypeVar('T', bound=DeclarativeBase)


class BaseRepository(t.Generic[T]):
    """
    Base repository class
    Exceptions are raised from sqlalchemy.exc
    Every session operations are flushed
    """

    REGISTRY: dict[str, t.Type['BaseRepository[T]']] = {}
    MODEL_CLASS: t.Type[T]
    BATCH_SIZE: int = 1000

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.MODEL_CLASS.__name__ in BaseRepository.REGISTRY:
            raise KeyError(f'Repository for model {cls.MODEL_CLASS.__name__} already exists in registry')
        BaseRepository.REGISTRY[cls.MODEL_CLASS.__name__] = cls

    def __init__(self, session: Session):
        self.session = session

    @classmethod
    def get_repository_from_model(cls, session, model: t.Type[T]) -> 'BaseRepository[T]':
        if model.__name__ in BaseRepository.REGISTRY:
            return BaseRepository.REGISTRY[model.__name__](session)
        new_repo = cls(session)
        new_repo.MODEL_CLASS = model
        return new_repo

    def _convert_params_to_model_fields(self, **params) -> list[ColumnElement]:
        result = []
        for name, value in params.items():
            field = getattr(self.MODEL_CLASS, name)
            result.append(t.cast(ColumnElement, field == value))
        return result

    def _validate_type(self, instances: list[T]) -> bool:
        if len(instances) > self.BATCH_SIZE:
            raise ValueError('Batch size exceeded')
        if not all([isinstance(instance, self.MODEL_CLASS) for instance in instances]):
            raise ValueError(f'Not all models are instance of class {self.MODEL_CLASS.__name__}')
        return True

    def _flush_obj(self, obj):
        self.session.add(obj)
        with self.session.begin_nested():
            self.session.flush()

    def get_or_create(self, **params) -> tuple[T, bool]:
        try:
            return self.get(*self._convert_params_to_model_fields(**params)), False
        except NoResultFound:
            return self.create(**params), True

    def get_query(
        self,
        *where_args: ColumnElement,
        joins: list | None = None,
        select: t.Tuple[ColumnElement] | None = None,
        order_by=None,
    ) -> sa.Select:
        query = sa.select(select if select else self.MODEL_CLASS).where(*where_args).order_by(order_by)

        if joins:
            for join in joins:
                query = query.join(*join) if isinstance(join, tuple) else query.join(join)
        return query

    # read methods
    def get(self, *where: ColumnElement, joins: list | None = None) -> T:
        """
        :returns: one
        :raises NoResultFound: if nothing was found
        :raises MultipleResultsFound: if found more than one record
        """
        stmt = self.get_query(*where, joins=joins)
        return self.session.scalars(stmt).one()

    def get_or_none(self, *where: ColumnElement, joins: list | None = None) -> T | None:
        stmt = self.get_query(*where, joins=joins)
        return self.session.scalars(stmt).one_or_none()

    def find(self, *where, joins: list | None = None, order_by=None) -> t.Sequence[T]:
        stmt = self.get_query(*where, joins=joins, order_by=order_by)
        return self.session.scalars(stmt).all()

    # write methods
    def create(self, **params) -> T:
        obj = self.MODEL_CLASS(**params)
        self._flush_obj(obj)
        return obj

    def create_batch(self, instances: list[T]) -> list[T]:
        for chunk in more_itertools.chunked(instances, self.BATCH_SIZE):
            with self.session.begin_nested():
                self._validate_type(chunk)
                self.session.add_all(chunk)
                self.session.flush()
        return instances

    def create_batch_from_dicts(self, data: list[dict]) -> list[T]:
        instances = []
        for chunk in more_itertools.chunked(data, self.BATCH_SIZE):
            result = [self.create(**item) for item in chunk]
            instances.extend(result)
        return instances
