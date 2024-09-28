try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo
from typing import Any, Optional, Union, Type, Callable, List, TypeVar
import pytz
import datetime
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth import get_user_model

from .middleware import get_request_user
from .exceptions import ConfigurationError, UTZError


DjangoModel = TypeVar("DjangoModel", bound=models.Model)
UserModel = TypeVar("UserModel", bound=AbstractBaseUser)


def validate_timezone(value: Any) -> Union[str, datetime.tzinfo]:
    """
    Validator to check if a timezone is valid.

    :param value: Timezone value to validate
    :raises: ValidationError if the value is not a valid timezone
    :return: The value if it is a valid timezone
    """
    if not is_timezone_valid(value):
        raise ValidationError("Invalid timezone.")
    return value


def is_timezone_valid(timezone: Union[str, datetime.tzinfo]) -> bool:
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


def get_attr_by_traversal(
    obj: object, traversal_path: str, default=None
) -> Optional[Any]:
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
        attrs = traversal_path.split(".")
        for attr in attrs:
            obj = getattr(obj, attr)
        return obj
    except AttributeError:
        return default


def is_datetime_field(model: Type[DjangoModel], field_name: str) -> bool:
    """
    Checks if the given field name is a datetime field in the model.

    :param model: The model to check.
    :param field_name: The name of the field to check.
    :return: True if the field is a datetime field, False otherwise.
    """
    field = model._meta.get_field(field_name)
    return issubclass(type(field), models.DateTimeField)


def is_time_field(model: Type[DjangoModel], field_name: str) -> bool:
    """
    Checks if the given field name is a time field in the model.

    :param model: The model to check.
    :param field_name: The name of the field to check.
    :return: True if the field is a time field, False otherwise.
    """
    field = model._meta.get_field(field_name)
    return issubclass(type(field), models.TimeField)


def is_date_field(model: Type[DjangoModel], field_name: str) -> bool:
    """
    Checks if the given field name is a date field in the model.

    :param model: The model to check.
    :param field_name: The name of the field to check.
    :return: True if the field is a date field, False otherwise.
    """
    field = model._meta.get_field(field_name)
    return issubclass(type(field), models.DateField)


def is_user_model(model: Type[DjangoModel]) -> bool:
    """Check if the model is the project's user model."""
    return model == get_user_model()


class FunctionAttribute:
    """
    A descriptor class that returns the result of
    passing an object into a function as an attribute.
    """

    def __init__(self, func: Callable[..., Any]):
        if not callable(func):
            raise TypeError("Value must be a function.")
        self.func = func

    def __set_name__(self, objtype, name: str):
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        self.name = name

    def __get__(self, obj, objtype):
        return self.func(obj)


class ModelError(UTZError):
    """There was an error with the model"""

    pass


def get_user(model_instance: DjangoModel) -> Optional[AbstractBaseUser]:
    """
    Gets and returns the user whose timezone is to be used by the model instance.

    If  the `use_related_user_timezone` config is True and `related_user` is not set, the first
    user found that is related to the model instance is returned.

    If no related user is found, the request user is returned.

    :param model_instance: The model instance for which a related user is to be found.
    :return: The user whose timezone is to be used by the model instance.
    """
    # Initially, assume that the object passed is a user object.
    user = model_instance
    instance_cls = type(model_instance)

    if is_user_model(instance_cls):
        return user

    from .decorators.models import get_user_model_config

    if get_user_model_config(instance_cls, "use_related_user_timezone", False):
        # Get the user object as specified by the `related_user` config
        # or by finding the user field in the model and its related models
        related_user = get_user_model_config(
            instance_cls, "related_user"
        ) or find_user_field(instance_cls)

        if not related_user:
            if get_user_model_config(instance_cls, "related_user"):
                raise ConfigurationError(
                    f"Make sure to set the `related_user` config to the name or traversal path of the user field in {instance_cls.__name__}."
                )
            raise ModelError(
                f"No relation to the User model was found in {instance_cls.__name__}"
            )

        user = get_attr_by_traversal(model_instance, related_user)
    else:
        user = get_request_user()
    return user


def find_user_field(model: Type[DjangoModel]) -> Optional[str]:
    """
    Finds and returns the traversal path to the first user field found
    in the model or its related models.

    This method assumes that the user is a foreign key or one-to-one field.
    """
    field_paths = []

    def find_user_related_field(model: Type[DjangoModel]) -> Optional[str]:
        """
        Finds and returns the user related field traversal path
        in the given model or its related models.
        """
        # First check all the fields in the model for the user field
        # If the user field is found, return the field path (Surface-level search)
        for field in model._meta.fields:
            if not is_user_model(field.related_model):
                continue
            field_paths.append(field.name)
            return ".".join(field_paths)

        # If the user field was not found at surface level,
        # check each field's related model (if any).
        for field in model._meta.fields:
            related_model = field.related_model
            if related_model and isinstance(
                field, (models.ForeignKey, models.OneToOneField)
            ):
                field_paths.append(field.name)

                if is_user_model(related_model):
                    return ".".join(field_paths)
                else:
                    # If the field is not the user field, recursively check the field's
                    # related model for the user field, both at surface level and in its related models (if any).
                    return find_user_related_field(related_model)

        # If the user field was not found in the model or its related models, pop the last field path and return.
        if field_paths:
            field_paths.pop()
        return

    return find_user_related_field(model)


def get_datetime_fields(model: Type[DjangoModel]) -> List[str]:
    """Returns a list of the datetime fields in the given model."""
    return [
        field.name
        for field in model._meta.fields
        if isinstance(field, models.DateTimeField)
    ]
