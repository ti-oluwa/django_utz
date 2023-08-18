import zoneinfo
import pytz
from django.db import models
from django.core.exceptions import ValidationError



def validate_timezone(value):
    """
    Validator to check if a timezone is valid.

    :param value: Timezone value to validate
    :raises: ValidationError if the value is not a valid timezone
    """
    if not is_timezone_valid(value):
        raise ValidationError("Invalid timezone.")


def is_timezone_valid(timezone_name: str):
    """
    Returns whether timezone_name is a valid timezone.

    :param timezone_name: timezone name
    :return: True if timezone_name is a valid timezone, False otherwise.
    """
    is_pytz = False
    is_zoneinfo = False
    try:
        pytz.timezone(timezone_name)
        is_pytz = True
    except pytz.exceptions.UnknownTimeZoneError:
        pass
    try:
        zoneinfo.ZoneInfo(timezone_name)
        is_zoneinfo = True
    except Exception:
        pass
    return is_pytz or is_zoneinfo


def final(method):
    """Decorator to mark a method as final. Not to be overridden."""

    def wrapper(*args, **kwargs):
        raise NotImplementedError(f"{method.__name__} cannot be overridden.")

    return wrapper


def get_attr_by_traversal(obj: object, traversal_path: str, default=None):
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
    
    traversal_path = "b.c.d"
    a = A()
    d = get_attr_by_traversal(a, traversal_path)
    ```
    """
    try:
        attrs = traversal_path.split('.')
        for attr in attrs:
            obj = getattr(obj, attr)
        return obj
    except AttributeError:
        return default


def is_datetime_field(model: models.Model, field_name: str):
    """
    Checks if the given field name is a datetime field in the model.

    :param model: The model to check.
    :param field_name: The name of the field to check.
    :return: True if the field is a datetime field, False otherwise.
    """
    field = model._meta.get_field(field_name)
    return issubclass(field.__class__, models.DateTimeField)


def is_time_field(model: models.Model, field_name: str):
    """
    Checks if the given field name is a time field in the model.

    :param model: The model to check.
    :param field_name: The name of the field to check.
    :return: True if the field is a time field, False otherwise.
    """
    field = model._meta.get_field(field_name)
    return issubclass(field.__class__, models.TimeField)