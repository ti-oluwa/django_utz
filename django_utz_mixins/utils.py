from django.core.exceptions import ImproperlyConfigured
import pytz
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
    try:
        pytz.timezone(timezone_name)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False


def final(method):
    """Decorator to mark a method as final. Not to be overridden."""

    def wrapper(*args, **kwargs):
        raise NotImplementedError(f"{method.__name__} cannot be overridden.")

    return wrapper