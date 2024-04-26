"""Utility functions for `django_utz` decorators"""
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo
from typing import Any, Callable, TypeVar
import pytz
import datetime
from django.db import models
from django.core.exceptions import ValidationError
import functools

from .bases import UTZDecorator


def validate_timezone(value: Any) -> str | datetime.tzinfo:
    """
    Validator to check if a timezone is valid.

    :param value: Timezone value to validate
    :raises: ValidationError if the value is not a valid timezone
    :return: The value if it is a valid timezone
    """
    if not is_timezone_valid(value):
        raise ValidationError("Invalid timezone.")
    return value


def is_timezone_valid(timezone: str | datetime.tzinfo) -> bool:
    """
    Returns whether timezone is a valid timezone.

    :param timezone: timezone info or name
    :return: True if timezone is a valid, False otherwise.
    """
    if isinstance(timezone, datetime.tzinfo):
        return True
    is_pytz = False
    is_zoneinfo = False
    try:
        pytz.timezone(timezone)
        is_pytz = True
    except pytz.exceptions.UnknownTimeZoneError:
        pass
    try:
        zoneinfo.ZoneInfo(timezone)
        is_zoneinfo = True
    except Exception:
        pass
    return is_pytz or is_zoneinfo


def get_attr_by_traversal(obj: object, traversal_path: str, default=None) -> object | Any | None:
    """
    Get an attribute of an object by traversing the object using the traversal path.
    
    :param obj: The object to traverse.
    :param traversal_path: The traversal path to the attribute. For example: "b.c.d"
    :param default: The default value to return if the attribute is not found.

    #### For example:
    ```
    class A:
        b = B()
    
    class B:
        c = C()

    class C:
        d = D()

    class D:
        def __init__(self):
            self.x = 10
    
    traversal_path = "b.c.d.x"
    a = A()
    x = get_attr_by_traversal(a, traversal_path)
    print(x) # 10
    ```
    """
    try:
        attrs = traversal_path.split('.')
        for attr in attrs:
            obj = getattr(obj, attr)
        return obj
    except AttributeError:
        return default


def is_datetime_field(model: type[models.Model], field_name: str) -> bool:
    """
    Checks if the given field name is a datetime field in the model.

    :param model: The model to check.
    :param field_name: The name of the field to check.
    :return: True if the field is a datetime field, False otherwise.
    """
    field = model._meta.get_field(field_name)
    return issubclass(field.__class__, models.DateTimeField)


def is_time_field(model: type[models.Model], field_name: str) -> bool:
    """
    Checks if the given field name is a time field in the model.

    :param model: The model to check.
    :param field_name: The name of the field to check.
    :return: True if the field is a time field, False otherwise.
    """
    field = model._meta.get_field(field_name)
    return issubclass(field.__class__, models.TimeField)


def is_date_field(model: type[models.Model], field_name: str) -> bool:
    """
    Checks if the given field name is a date field in the model.

    :param model: The model to check.
    :param field_name: The name of the field to check.
    :return: True if the field is a date field, False otherwise.
    """
    field = model._meta.get_field(field_name)
    return issubclass(field.__class__, models.DateField)



Class = TypeVar("Class", bound=type[object])


def transform_utz_decorator(decorator: type[UTZDecorator]) -> Callable[[Class], Class]:
    """
    Transforms class type utz decorator to a function type decorator.

    Using a utz decorator directly on a class will require that the class be instantiated
    before the decorator logic is applied. This is not ideal as the decorator logic should be
    applied to the decorated class itself and a modified class should be returned.

    A decorator wrapper function is returned that takes a class, applies the wrapped utz decorator logic,
    and returns the modified class.
    """
    @functools.wraps(decorator)
    def decorator_wrapper(cls: Class) -> Class:
        """Wrapper function that applies the utz decorator to the decorated class."""
        return decorator(cls)()
    
    return decorator_wrapper
