"""Utility functions/classes for django_utz"""
try:
    import zoneinfo
except:
    from backports import zoneinfo
import pytz
import datetime
from django.utils import timezone
from django.db import models
from django.core.exceptions import ValidationError


def validate_timezone(value):
    """
    Validator to check if a timezone is valid.

    :param value: Timezone value to validate
    :raises: ValidationError if the value is not a valid timezone
    :return: The value if it is a valid timezone
    """
    if not is_timezone_valid(value):
        raise ValidationError("Invalid timezone.")
    return value


def is_timezone_valid(timezone: str | datetime.tzinfo):
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


def is_date_field(model: models.Model, field_name: str):
    """
    Checks if the given field name is a date field in the model.

    :param model: The model to check.
    :param field_name: The name of the field to check.
    :return: True if the field is a date field, False otherwise.
    """
    field = model._meta.get_field(field_name)
    return issubclass(field.__class__, models.DateField)


class utzdatetime(datetime.datetime):
    """Custom datetime class that can be independent of settings.USE_TZ"""
    convert_to_local_time = False

    @classmethod
    def from_datetime(cls, _datetime: datetime.datetime):
        """Returns a utzdatetime object from a datetime.datetime object"""
        if not isinstance(_datetime, datetime.datetime):
            raise TypeError(f"_datetime expected datetime.datetime object, got {type(_datetime)}")
        if timezone.is_naive(_datetime):
            default_timezone = timezone.get_default_timezone()
            _datetime = timezone.make_aware(_datetime, default_timezone)
        return cls(
            year=_datetime.year,
            month=_datetime.month,
            day=_datetime.day,
            hour=_datetime.hour,
            minute=_datetime.minute,
            second=_datetime.second,
            microsecond=_datetime.microsecond,
            tzinfo=_datetime.tzinfo
        )

    def regard_usetz(self):
        """Respect settings.USE_TZ when converting to local time"""
        self.convert_to_local_time = True
        return self

    def disregard_usetz(self):
        """Remain unaffected by settings.USE_TZ when converting to local time"""
        self.convert_to_local_time = False
        return self