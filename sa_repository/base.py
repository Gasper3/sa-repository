import typing as t

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

__all__ = ['BaseRepository']

T = t.TypeVar('T')


class BaseRepository(t.Generic[T]):
    """
    Base repository class
    Every exception is raised from sqlalchemy.exc
    Every session operations are flushed NOT committed
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

    def _validate_type(self, instances: list):
        if not all([isinstance(instance, self.MODEL_CLASS) for instance in instances]):
            raise ValueError(f'Not all models are instance of class {self.MODEL_CLASS.__name__}')
        return True

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
