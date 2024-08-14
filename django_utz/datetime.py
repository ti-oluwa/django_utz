from django.utils import timezone
import datetime


class utzdatetime(datetime.datetime):
    """Custom datetime class that can be independent of settings.USE_TZ"""

    convert_to_local_time = False

    @classmethod
    def from_datetime(cls, _datetime: datetime.datetime):
        """Constructs and returns a `utzdatetime` object from a `datetime.datetime` object"""
        if not isinstance(_datetime, datetime.datetime):
            raise TypeError(
                f"_datetime expected datetime.datetime object, got {type(_datetime)}"
            )
        if timezone.is_naive(_datetime):
            default_timezone = timezone.get_default_timezone()
            _datetime = timezone.make_aware(_datetime, default_timezone)
        return cls(
            year=_datetime.year,
            month=_datetime.month,
            day=_datetime.day,
            hour=_datetime.hour,
            minute=_datetime.minute,
            second=_datetime.second,
            microsecond=_datetime.microsecond,
            tzinfo=_datetime.tzinfo,
        )

    def regard_usetz(self):
        """Respect `settings.USE_TZ` when converting to local time"""
        self.convert_to_local_time = True
        return self

    def disregard_usetz(self):
        """Remain unaffected by `settings.USE_TZ` when converting to local time"""
        self.convert_to_local_time = False
        return self
