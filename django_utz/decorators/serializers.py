from rest_framework import serializers
from typing import Any, Dict, Optional, Set, TypeVar, Type, List
import inspect
import datetime

from ..config_factories import (
    make_utz_config_getter,
    make_utz_config_setter,
    make_utz_config_validator_registrar,
)
from ..utils import ModelError
from ..exceptions import ConfigurationError
from ..serializer_fields import UTZDateTimeField
from .models import get_model_config

DRFModelSerializer = TypeVar("DRFModelSerializer", bound=serializers.ModelSerializer)


def get_serializer_model(serializer_class: Type[DRFModelSerializer]):
    """Returns the model of a model serializer class."""
    return serializer_class.Meta.model


def get_serializer_fields(serializer_class: Type[DRFModelSerializer]) -> Set[str]:
    """Returns the fields of a model serializer class."""
    model = get_serializer_model(serializer_class)

    if hasattr(serializer_class.Meta, "fields"):
        field_names = set(serializer_class.Meta.fields)
    else:
        all_fields = set(field.name for field in model._meta.get_fields())
        field_names = all_fields

    if hasattr(serializer_class.Meta, "exclude"):
        exclude = set(serializer_class.Meta.exclude)
        field_names = field_names - exclude
    return field_names


SERIALIZER_CLASS_CONFIGS = ("auto_add_fields", "datetime_format")
REQUIRED_SERIALIZER_CLASS_CONFIGS = ("auto_add_fields",)
SERIALIZER_CLASS_CONFIG_VALIDATORS = {}

get_serializer_class_config = make_utz_config_getter(SERIALIZER_CLASS_CONFIG_VALIDATORS)
set_serializer_class_config = make_utz_config_setter(
    SERIALIZER_CLASS_CONFIGS, SERIALIZER_CLASS_CONFIG_VALIDATORS
)
serializer_class_config_validator = make_utz_config_validator_registrar(
    SERIALIZER_CLASS_CONFIG_VALIDATORS
)


@serializer_class_config_validator(config="auto_add_fields")
def validate_auto_add_fields(value: Any) -> None:
    if not isinstance(value, bool):
        raise ConfigurationError("auto_add_fields must be a boolean")
    return None


@serializer_class_config_validator(config="datetime_format")
def validate_datetime_format(value: Any) -> None:
    if not isinstance(value, str):
        raise ConfigurationError("datetime_format must be a string")

    try:
        datetime.datetime.now().strftime(value)
    except ValueError:
        raise ConfigurationError(f"Invalid datetime format: {value}")
    return None


def check_serializer_class(
    serializer_class: Type[DRFModelSerializer],
    required_configs: Optional[List[str]] = None,
) -> DRFModelSerializer:
    """
    Check if the model serializer class is properly setup.

    :param serializer_class: The model serializer class to check.
    :param required_configs: A list of required configurations that must be set in the model serializer's UTZMeta class.
    :return: The model serializer class if it is valid.
    """
    if not issubclass(serializer_class, serializers.ModelSerializer):
        raise TypeError(
            f"'{serializer_class.__name__}' is not a model serializer class"
        )
    else:
        model = get_serializer_model(serializer_class)
        try:
            model_is_decorated = get_model_config(model, "_decorated", False)
        except AttributeError:
            model_is_decorated = False

        if not model_is_decorated:
            raise ModelError(
                f"Serializer's model {model.__name__}, has not been decorated with a `ModelDecorator`"
            )

        if not hasattr(serializer_class, "UTZMeta"):
            raise AttributeError("Model serializer class must have a UTZMeta class")

        if not inspect.isclass(model.UTZMeta):
            raise ConfigurationError("UTZMeta must be a class")

        for config in required_configs:
            if not getattr(serializer_class.UTZMeta, config, None):
                raise ConfigurationError(
                    f"'{config}' must be set in the model serializer's UTZMeta class"
                )
    return serializer_class


def prepare_serializer_class(
    serializer_class: Type[DRFModelSerializer],
) -> Type[DRFModelSerializer]:
    """
    Prepare the serializer class for use. Makes necessary modifications to the serializer class.
    """
    datetime_fields = get_serializer_model(serializer_class).UTZMeta.datetime_fields
    serializer_fields = get_serializer_fields(serializer_class)

    # If the serializer has no fields, return it as is
    if not serializer_fields:
        return serializer_class

    if get_serializer_class_config(serializer_class, "auto_add_fields", False):
        for fieldname in datetime_fields:
            # Skip fields that are not included in the serializer
            if fieldname not in serializer_fields:
                continue
            # If field is already defined in the serializer, skip it
            if hasattr(serializer_class, fieldname):
                continue

            extra_kwargs = getattr(serializer_class.Meta, "extra_kwargs", {}).get(
                fieldname, {}
            )

            utzdatetime_field = get_utzdatetime_field(serializer_class, extra_kwargs)
            setattr(serializer_class, fieldname, utzdatetime_field)

    return serializer_class


def get_utzdatetime_field(
    serializer_class: Type[DRFModelSerializer],
    extra_kwargs: Optional[Dict[str, Any]] = None,
) -> UTZDateTimeField:
    """
    Returns a `UTZDateTimeField`

    :param serializer_class: The model serializer class.
    :param extra_kwargs: Extra keyword arguments to pass to the `UTZDateTimeField` constructor.
    :return: A `UTZDateTimeField` instance.
    """
    extra_kwargs = extra_kwargs or {}
    datetime_format = get_serializer_class_config(serializer_class, "datetime_format")

    if datetime_format and "format" not in extra_kwargs:
        extra_kwargs.update({"format": datetime_format})
    return UTZDateTimeField(**extra_kwargs)


def modelserializer(
    serializer_class: Type[DRFModelSerializer],
) -> Type[DRFModelSerializer]:
    """
    Model serializer class decorator

    Auto adds user timezone aware datetime fields to the serializer class
    in-place of the normal datetime fields, if `auto_add_fields` config is set as True.

    The decorated model serializer must have a `UTZMeta` class with the following attributes:
    - `auto_add_fields`: Optional. A boolean that determines if user timezone aware datetime fields should be automatically added to the serializer.
    - `datetime_format`: Optional. A string that determines the output format for the user timezone aware datetime fields.

    Example Usage:
    ```python
    from rest_framework import serializers
    from django_utz.decorators import modelserializer

    from .models import Article

    @modelserializer
    class ArticleSerializer(serializers.ModelSerializer):
        class Meta:
            model = Article
            fields = "__all__"
            exclude = ("updated_at",)
            extra_kwargs = {
                "published_at": {"read_only": True},
            }

        class UTZMeta:
            auto_add_fields = True
            datetime_format = "%Y-%m-%dT%H:%M:%S%z"
    ```
    """
    check_serializer_class(serializer_class, REQUIRED_SERIALIZER_CLASS_CONFIGS)
    prepared_serializer_class = prepare_serializer_class(serializer_class)
    prepared_serializer_class.UTZMeta._decorated = True
    return prepared_serializer_class
