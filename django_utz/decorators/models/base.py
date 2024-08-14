import inspect
from typing import Any, List, Optional, TypeVar, Type
from django.db import models

from ...exceptions import ConfigurationError

DjangoModel = TypeVar("DjangoModel", bound=models.Model)


def check_model_class(
    model_class: Type[DjangoModel], required_configs: Optional[List[str]] = None
) -> Type[DjangoModel]:
    """
    Check if model and model configuration is valid. Returns the model if it is valid.

    :param model: The model to check
    :return: The model if it is valid
    """
    if not issubclass(model_class, models.Model):
        raise TypeError(f"{model_class.__name__} is not a Django model")

    elif not hasattr(model_class, "UTZMeta"):
        raise AttributeError("Model must have a UTZMeta class")

    elif not inspect.isclass(model_class.UTZMeta):
        raise ConfigurationError("UTZMeta must be a class")

    for config in required_configs:
        if not getattr(model_class.UTZMeta, config, None):
            raise ConfigurationError(
                f"'{config}' must be set in the model's UTZMeta class"
            )
    return model_class
