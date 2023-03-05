import typing as t

import more_itertools
from sqlalchemy import Select, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, DeclarativeMeta

__all__ = ['BaseRepository']

T = t.TypeVar('T', bound=DeclarativeMeta)


class BaseRepository(t.Generic[T]):
    """
    Base repository class
    Exceptions are raised from sqlalchemy.exc
    Every session operations are flushed
    """

    REGISTRY = {}
    MODEL_CLASS: t.Type[T]
    BATCH_SIZE = 1000

    def __init_subclass__(cls, **kwargs):
        if cls.__name__ in BaseRepository.REGISTRY:
            raise KeyError(f'Class {cls.__name__} already exists in registry')
        BaseRepository.REGISTRY[cls.__name__] = cls

    def __init__(self, session: Session):
        self.session = session

    @classmethod
    def get_repository_from_model(cls, session, model):
        new_repo = cls(session)
        new_repo.MODEL_CLASS = model
        return new_repo

    def _convert_params_to_model_fields(self, **params):
        result = []
        for name, value in params.items():
            field = getattr(self.MODEL_CLASS, name)
            result.append(field == value)
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

    def _create_from_params(self, **params) -> T:
        obj = self.MODEL_CLASS(**params)
        self._flush_obj(obj)
        return obj

    def get_or_create(self, **params) -> tuple[T, bool]:
        try:
            return self.get(*self._convert_params_to_model_fields(**params)), False
        except NoResultFound:
            return self._create_from_params(**params), True

    # read methods
    def _simple_select(self, *where, join) -> Select:
        sel = select(self.MODEL_CLASS).where(*where)
        if join:
            sel = sel.join(join)
        return sel

    def get(self, *where, join=None) -> T:
        """
        :returns: one
        :raises NoResultFound: if nothing was found
        :raises MultipleResultsFound: if found more than one record
        """
        stmt = self._simple_select(*where, join=join)
        return self.session.scalars(stmt).one()

    def find(self, *where, join=None) -> t.Sequence[T]:
        stmt = self._simple_select(*where, join=join)
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

    def create_batch_from_dicts(self, data: list[dict]):
        instances = []
        for chunk in more_itertools.chunked(data, self.BATCH_SIZE):
            result = [self._create_from_params(**item) for item in chunk]
            instances.extend(result)
        return instances

    def update(self, instance: T, **params) -> T:
        self._validate_type([instance])
        for col, value in params.items():
            setattr(instance, col, value)
        self._flush_obj(instance)
        return instance
