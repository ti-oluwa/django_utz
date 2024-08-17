from typing import Any, Dict, Optional, Type, List, Callable, TypeVar, Union

from .exceptions import ConfigurationError


Validator = Callable[[Any], None]
D = TypeVar("D")


def make_utz_config_getter(validators: Optional[Dict[str, Validator]] = None):
    """
    Create a getter function for getting configuration values from a utz decorated class.

    :param validators: A list of validation functions to validate configuration values.
        These functions should raise a `ConfigurationError` if the value is invalid.
    """
    validators = validators or {}

    def getter(
        cls: Type[object], config: str, default: Optional[D] = None
    ) -> Optional[Union[Any, D]]:
        """
        Get the value of a utz configuration from the class.

        :param cls: The class to get the configuration from.
        :param config: The configuration to get.
        :param default: The default value to return if the configuration is not set.
        :return: The value of the configuration or `default`.
        """
        validator = validators.get(config)
        value = getattr(cls.UTZMeta, config, default)
        if value is not None and validator:
            validator(value)
        return value

    return getter


def make_utz_config_setter(
    allowed_configs: List[str], validators: Optional[Dict[str, Validator]] = None
):
    """
    Create a setter function for setting configuration values on a utz decorated class.

    :param allowed_configs: A list of allowed configurations that can be set.
    :param validators: A list of validation functions to validate the configuration values.
    """
    validators = validators or {}

    def setter(cls: Type[object], config: str, value: Any) -> None:
        """
        Sets a configuration's value on the class.

        :param cls: The class to set the configuration on.
        :param attr: The configuration to set.
        :param value: The value to set.
        """

        if config != "_decorated" and config not in allowed_configs:
            raise ConfigurationError(f"Invalid config: {config}")

        validator = validators.get(config)
        if value is not None and validator:
            validator(value)

        setattr(cls.UTZMeta, config, value)
        return None

    return setter


def make_utz_config_validator_registrar(registry: Dict[str, Validator]):
    """
    Create a function for registering a configuration validator in the registry.

    :param registry: The registry to register the validator in.
    """

    def register_validator(
        validator: Validator, *, config: Optional[str] = None
    ) -> None:
        """
        Register a configuration validator in the registry.

        :param validator: The validator to register.
        :param config: The configuration to register the validator for.
        """
        if config is None:
            config = validator.__name__.removeprefix("validate_")

        registry[config] = validator
        return None

    return register_validator
