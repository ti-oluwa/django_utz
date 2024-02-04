from abc import ABC, abstractmethod
from typing import Any


class UTZDecorator(ABC):
    """Abstract base class for all `django_utz` decorators."""
    all_configs = ()
    required_configs = ()
    __slots__ = ()

    def __init__(self) -> None:
        self.set_config("_decorated", True)

    @abstractmethod
    def __call__(self) -> Any:
        """
        The method that is called when the decorator is used on a model or serializer.

        :return: The decorated model or serializer.
        """
        pass

    @abstractmethod
    def set_config(self, attr: str, value: Any) -> None:
        """
        Sets a configuration attribute on the model or serializer.

        :param attr: The attribute to set.
        :param value: The value to set.
        """
        pass

    @abstractmethod
    def get_config(self, attr: str, default: Any = None) -> Any | None:
        """
        Get the value of a configuration attribute from the model or serializer.

        :param attr: The attribute to get.
        :param default: The default value to return if the attribute is not set.
        :return: The value of the attribute or `default`.
        """
        pass

