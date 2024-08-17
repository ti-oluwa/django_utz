import zoneinfo
from rest_framework import serializers
from django.conf import settings
from django.utils.itercompat import is_iterable
import pytz

from .utils import get_user
from .exceptions import ConfigurationError


class UTZDateTimeField(serializers.DateTimeField):
    """
    `serializers.DateTimeField` that converts input datetime to
    server's timezone(settings.TIMEZONE) before storage
    and converts back to the preferred user's local timezone on output.

    if settings.USE_TZ is False, server's timezone is assumed to be UTC

    #### Example:
    ```
    class BookSerializer(serializers.ModelSerializer):
        created_at = UTZDateTimeField(format="%Y-%m-%d %H:%M:%S %Z (%z)")
        updated_at = UTZDateTimeField(format="%Y-%m-%d %H:%M:%S %Z (%z)")

        class Meta:
            model = Book
            fields = "__all__"
            extra_kwargs = {
                "created_at": {"read_only": True},
                "updated_at": {"read_only": True},
            }
    ```
    """

    def __new__(cls, *args, **kwargs):
        new_field = super().__new__(*args, **kwargs)
        new_field._call_count = 0
        return new_field

    def to_representation(self, value):
        instance = self.root.instance
        # If the instance is a queryset, get the current instance from the queryset
        if is_iterable(instance):
            instance = instance[self._call_count]
            self._call_count += 1

        instance_model_is_decorated = getattr(
            type(instance), "UTZMeta", None
        ) and getattr(type(instance).UTZMeta, "_decorated", False)
        if not instance_model_is_decorated:
            raise ConfigurationError(
                f"Model '{type(instance).__name__}', has not been decorated with a `ModelDecorator`"
            )

        user = get_user(instance)
        if user:
            self.timezone = user.utz
        return super().to_representation(value)

    def to_internal_value(self, value):
        if getattr(settings, "USE_DEPRACATED_PYTZ", False):
            server_timezone = (
                pytz.timezone(settings.TIME_ZONE) if settings.USE_TZ else pytz.utc
            )
        else:
            server_timezone = (
                zoneinfo.ZoneInfo(settings.TIME_ZONE)
                if settings.USE_TZ
                else zoneinfo.ZoneInfo("UTC")
            )
        return super().to_internal_value(value).astimezone(server_timezone)
