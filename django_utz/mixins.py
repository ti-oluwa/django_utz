import pytz
import datetime
from typing import TypeVar
from django.conf import settings

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

from .utils import is_timezone_valid
from .datetime import utzdatetime


DateTime = TypeVar("DateTime", bound=datetime.datetime)


class UserModelUTZMixin:
    """Adds necessary utz methods and properties to a user model"""

    @property
    def utz(self):
        """
        The user's timezone info as a `pytz.tzinfo` or `zoneinfo.ZoneInfo` object.

        if settings.USE_DEPRECATED_PYTZ is True, then the user's timezone info is returned as a pytz.tzinfo object.
        Otherwise, it is returned as a zoneinfo.ZoneInfo object.
        """
        tz = getattr(self, self.UTZMeta.timezone_field)

        if tz and isinstance(tz, datetime.tzinfo):
            zone_str = str(tz)
        elif tz and isinstance(tz, str):
            if not is_timezone_valid(tz):
                raise ValueError(f"Invalid timezone: {tz}.")
            zone_str = tz

        if getattr(settings, "USE_DEPRECATED_PYTZ", False) is True:
            return pytz.timezone(zone_str)

        return zoneinfo.ZoneInfo(zone_str)

    def to_local_timezone(self, _datetime: DateTime) -> utzdatetime:
        """
        Adjust datetime.datetime object to user's local timezone.
        If the user's timezone is not set, the datetime object is returned as is.

        :param _datetime: `datetime.datetime` object
        :return: `utzdatetime` object

        datetime object returned is not affected by `settings.USE_TZ`.
        To change this behavior do:
        ```
        import datetime
        utz_datetime = user.to_local_timezone(datetime.datetime.now())
        utz_datetime.regard_usetz()
        ```
        """
        utz_dt = utzdatetime.from_datetime(_datetime)
        user_tz = self.utz
        if user_tz:
            return utz_dt.astimezone(user_tz)
        return utz_dt
