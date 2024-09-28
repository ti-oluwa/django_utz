import inspect
from typing import Any, Type, List, Optional, Callable
from django.core.exceptions import FieldDoesNotExist
from django.db import models

from ..config_factories import (
    make_utz_config_getter,
    make_utz_config_setter,
    make_utz_config_validator_registrar,
)
from ..utils import is_datetime_field, validate_timezone, ModelError
from ..datetime import utzdatetime
from ..exceptions import ConfigurationError
from ..utils import (
    get_user,
    is_user_model,
    FunctionAttribute,
    get_datetime_fields,
    DjangoModel,
    UserModel,
)
from ..mixins import UserModelUTZMixin


def check_model(
    model: Type[DjangoModel], required_configs: Optional[List[str]] = None
) -> Type[DjangoModel]:
    """
    Check if model and model configuration is valid. Returns the model if it is valid.

    :param model: The model to check
    :return: The model if it is valid
    """
    if not issubclass(model, models.Model):
        raise TypeError(f"{model.__name__} is not a Django model")

    elif not hasattr(model, "UTZMeta"):
        raise AttributeError("Model must have a UTZMeta class")

    elif not inspect.isclass(model.UTZMeta):
        raise ConfigurationError("UTZMeta must be a class")

    for config in required_configs:
        if not getattr(model.UTZMeta, config, None):
            raise ConfigurationError(
                f"'{config}' must be set in the model's UTZMeta class"
            )
    return model


##############
# USER MODEL #
##############

USER_MODEL_CONFIGS = ("timezone_field",)
REQUIRED_USER_MODEL_CONFIGS = USER_MODEL_CONFIGS
USER_MODEL_CONFIG_VALIDATORS = {}

get_user_model_config = make_utz_config_getter(USER_MODEL_CONFIG_VALIDATORS)
set_user_model_config = make_utz_config_setter(
    USER_MODEL_CONFIGS, USER_MODEL_CONFIG_VALIDATORS
)
user_model_config_validator = make_utz_config_validator_registrar(
    USER_MODEL_CONFIG_VALIDATORS
)


@user_model_config_validator(config="timezone_field")
def validate_timezone_field(value: Any) -> None:
    if not isinstance(value, str):
        raise ConfigurationError("Value for 'timezone_field' should be of type str")
    return None


def check_user_model(user_model: Type[UserModel]) -> Type[UserModel]:
    """Ensures that the model in which this mixin is used is the project's user model"""
    check_model(user_model, REQUIRED_USER_MODEL_CONFIGS)

    if not is_user_model(user_model):
        raise ModelError(
            f"Model '{user_model.__name__}' is not the project's user model"
            "Ensure that the decorated model is the one defined in settings.AUTH_USER_MODEL"
        )
    return user_model


def prepare_user_model_class(user_model: Type[UserModel]) -> UserModel:
    # Add timezone validator to the `timezone_field`` if not already added
    try:
        timezone_field: str = get_user_model_config(user_model, "timezone_field")
        field = user_model._meta.get_field(timezone_field)
        if field and validate_timezone not in field.validators:
            field.validators = [*field.validators, validate_timezone]

    except FieldDoesNotExist:
        raise ModelError(
            f"Field '{timezone_field}' does not exist in model '{user_model.__name__}'"
        )

    user_model.__bases__ = (UserModelUTZMixin, *user_model.__bases__)
    return user_model


def usermodel(user_model: Type[UserModel]) -> Type[UserModel]:
    """
    User model decorator.

    The user model must be decorated with this decorator for `django_utz` to work properly.
    The decorated model must have a `UTZMeta` class with the following attributes:
    - `timezone_field`: The name of the timezone field in the model.

    Example Usage:
    ```python
    from django.contrib.auth.models import AbstractUser
    from django_utz.decorators import usermodel

    @usermodel
    class User(AbstractUser):
        id = models.AutoField(primary_key=True)
        email = models.EmailField(unique=True)
        username = models.CharField(max_length=100)
        ...
        timezone = models.CharField(max_length=100)

        class UTZMeta:
            timezone_field = "timezone"
    ```
    """
    check_user_model(user_model)
    prepared_user_model_class = prepare_user_model_class(user_model)
    prepared_user_model_class.UTZMeta._decorated = True
    return prepared_user_model_class


#########
# MODEL #
#########

DEFAULT_ATTRIBUTE_SUFFIX = "utz"

MODEL_CONFIGS = (
    "datetime_fields",
    "attribute_suffix",
    "use_related_user_timezone",
    "related_user",
)
REQUIRED_MODEL_CONFIGS = ("datetime_fields",)
MODEL_CONFIG_VALIDATORS = {}

get_model_config = make_utz_config_getter(MODEL_CONFIG_VALIDATORS)
set_model_config = make_utz_config_setter(MODEL_CONFIGS, MODEL_CONFIG_VALIDATORS)
model_config_validator = make_utz_config_validator_registrar(MODEL_CONFIG_VALIDATORS)


@model_config_validator(config="datetime_fields")
def validate_datetime_fields(value: Any) -> None:
    if value != "__all__" and not isinstance(value, (list, tuple)):
        raise ConfigurationError(
            "'datetime_fields' should be a list, tuple or '__all__'"
        )
    return None


@model_config_validator(config="attribute_suffix")
def validate_attribute_suffix(value: Any) -> None:
    if not isinstance(value, str):
        raise ConfigurationError("'attribute_suffix' should be of type str")
    return None


@model_config_validator(config="use_related_user_timezone")
def validate_use_related_user_timezone(value: Any) -> None:
    if not isinstance(value, bool):
        raise ConfigurationError("'use_related_user_timezone' should be of type bool")
    return None


@model_config_validator(config="related_user")
def validate_related_user(value: Any) -> None:
    if not isinstance(value, str):
        raise ConfigurationError("'related_user' should be of type str")
    return None


def prepare_model(model: Type[DjangoModel]) -> Type[DjangoModel]:
    if get_model_config(model, "datetime_fields") == "__all__":
        set_model_config(model, "datetime_fields", get_datetime_fields(model))

    if not get_model_config(model, "attribute_suffix"):
        set_model_config(model, "attribute_suffix", DEFAULT_ATTRIBUTE_SUFFIX)

    if not get_model_config(model, "use_related_user_timezone"):
        set_model_config(model, "use_related_user_timezone", False)

    return update_model_attrs(model)


def make_func_for_field(
    model: Type[DjangoModel], datetime_field: str
) -> Callable[[models.Model], utzdatetime]:
    """
    Makes and returns a function that returns the value of the datetime field on a model instance
    in the user's local timezone.

    :param datetime_field: The name of the datetime field for which to make the function
    """
    suffix = get_model_config(model, "attribute_suffix")
    func_name = f"get_{datetime_field}_{suffix}"

    def func(instance: DjangoModel) -> utzdatetime:
        user = get_user(instance)
        if user is None:
            return utzdatetime.from_datetime(getattr(instance, datetime_field))
        return user.to_local_timezone(getattr(instance, datetime_field))

    func.__name__ = func_name
    func.__qualname__ = func_name
    return func


def update_model_attrs(model: Type[DjangoModel]) -> Type[DjangoModel]:
    """
    Updates the model with the read-only attributes for the datetime fields.

    :param model: The model to update
    """
    datetime_fields: List[str] = get_model_config(model, "datetime_fields")
    attribute_suffix: str = get_model_config(model, "attribute_suffix")

    for field in datetime_fields:
        if not is_datetime_field(model, field):
            raise ConfigurationError(
                f"Field '{field}' is not a datetime field in model '{model.__name__}'"
            )

        func = make_func_for_field(model, field)
        read_only_attr = FunctionAttribute(func)
        attr_name = f"{field}_{attribute_suffix}"
        setattr(model, attr_name, read_only_attr)
    return model


def model(model: Type[DjangoModel]) -> Type[DjangoModel]:
    """
    #### Model decorator.

    The decorated model must have a `UTZMeta` class with the following attributes:
    - `datetime_fields`: A list of the names of the datetime fields in the model or "__all__" to use all datetime fields.
    - `attribute_suffix`: Optional. The suffix to be added to the read-only attributes for utz versions  the datetime fields.
    Defaults to "utz".
    - `use_related_user_timezone`: Optional. A boolean indicating whether to use the timezone of the related user model.
    Defaults to False.
    - `related_user`: Optional. The name of the related user model if `use_related_user_timezone` is True.

    Example Usage:
    ```python
    from django.db import models
    from django_utz.decorators import model

    @model
    class Article(models.Model):
        title = models.CharField(max_length=100)
        content = models.TextField()
        author = models.ForeignKey("Author", on_delete=models.CASCADE)
        published_at = models.DateTimeField()
        updated_at = models.DateTimeField()

        class UTZMeta:
            datetime_fields = ("published_at", "updated_at")
            attribute_suffix = "local"
    ```
    """
    check_model(model, REQUIRED_MODEL_CONFIGS)
    prepared_model = prepare_model(model)
    prepared_model.UTZMeta._decorated = True
    return prepared_model
