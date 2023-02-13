# SQLAlchemy Repository for models
![tests workflow](https://github.com/Gasper3/sa-repository/actions/workflows/actions.yml/badge.svg)

This project contains simple base repository class for your models.  
All you need to do is:
1. Install this package `python -m pip install sa-repository`
2. Use it in your project
    ```python
    from sa_repository import BaseRepository
    from models import YourSAModel
    
    class SomeModelRepository(BaseRepository[YourSAModel]):
        pass
    ```

Base class contains some general methods to simplify your work with sqlalchemy models e.x
```python
var = SomeModelRepository(session).get(YourSAModel.attr == 'some_value')
```

If you don't want to create new repository classes, you can use `get_repository_from_model` method
```python
repository = BaseRepository.get_repository_from_model(db_session, SomeModel)
```
