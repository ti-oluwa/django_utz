import pytz

def is_timezone_valid(timezone_name: str):
    """
    Returns whether timezone_name is a valid timezone.

    :param timezone_name: timezone name
    :return: True if timezone_name is a valid timezone, False otherwise.
    """
    try:
        pytz.timezone(timezone_name)
        return True
    except pytz.UnknownTimeZoneError:
        return False
    

def final(method):
    """Decorator to mark a method as final. Not to be overridden."""

    def wrapper(*args, **kwargs):
        raise NotImplementedError(f"{method.__name__} cannot be overridden.")

    return wrapper