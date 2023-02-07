import typing as t

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
