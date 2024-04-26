from abc import ABC, abstractmethod
import inspect
from typing import Any, TypeVar
from django.db import models

from ..bases import UTZDecorator
from .exceptions import ModelConfigurationError

DjangoModel = TypeVar("DjangoModel", bound=models.Model)


class ModelDecorator(UTZDecorator, ABC):
    """
    Base class for all `django_utz` model decorators. 
    """
    all_configs = ()
    required_configs = ()
    __slots__ = ("model",)

    def __init__(self, model: DjangoModel) -> None:
        self.model = self.check_model(model)
        super().__init__()
    

    def __call__(self) -> DjangoModel:
        prepared_model = self.prepare_model()
        if not issubclass(prepared_model, models.Model):
            raise TypeError("prepare_model method must return a model")
        return prepared_model


    def check_model(self, model: DjangoModel) -> DjangoModel:
        """
        Check if model and model configuration is valid. Returns the model if it is valid.

        `self.model` should not be accessed in this method as it set by this method.

        :param model: The model to check
        :return: The model if it is valid
        """
        if not issubclass(model, models.Model):
            raise TypeError(f"{model.__name__} is not a Django model")
        
        if not hasattr(model, "UTZMeta"):
            raise AttributeError("Model must have a UTZMeta class")
        
        if not inspect.isclass(model.UTZMeta):
            raise ModelConfigurationError("UTZMeta must be a class")
        
        for config in self.required_configs:
            if not getattr(model.UTZMeta, config, None):
                raise ModelConfigurationError(f"'{config}' must be set in the model's UTZMeta class")
        return model


    @abstractmethod
    def prepare_model(self) -> DjangoModel:
        """
        Prepare the model for use. This where you can customize the model.

        :return: The model
        """
        pass

    
    def get_config(self, attr: str, default: Any = None) -> Any | None:
        """
        Get the value of a configuration attribute from the model.

        :param attr: The name of the configuration attribute
        :param default: The default value to return if the attribute is not set
        :return: The value of the configuration attribute
        """
        if not hasattr(self, "model"):
            raise AttributeError("Model not set")
        
        val = getattr(self.model.UTZMeta, attr, default)
        if val is not None and hasattr(self, f"validate_{attr}"):
            getattr(self, f"validate_{attr}")(val)
        return val


    def set_config(self, attr: str, value: Any) -> None:
        """
        Set the value of a configuration attribute in the model.
        
        :param attr: The name of the configuration attribute
        :param value: The value to set
        """
        if not hasattr(self, "model"):
            raise AttributeError("Model not set")
        
        if attr != "_decorated" and attr not in self.all_configs:
            raise ModelConfigurationError(f"Invalid config: {attr}")
        
        if value is not None and hasattr(self, f"validate_{attr}"):
            getattr(self, f"validate_{attr}")(value)

        setattr(self.model.UTZMeta, attr, value)
        return None

