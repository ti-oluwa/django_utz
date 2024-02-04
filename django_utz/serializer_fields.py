"""Provides custom serializer fields for converting datetime to user's local timezone on representation"""
import zoneinfo
from rest_framework import serializers
from django.conf import settings
import pytz
from django.db import models

from .decorators.models.utils import get_user
from .decorators.models.exceptions import ModelError


class UTZField:
    """
    Mixin for converting native serializer fields to a UTZField.
    """
    def __new__(cls, *args, **kwargs):
        new_field = super().__new__(*args, **kwargs)
        new_field._call_count = 0
        return new_field
    

    def to_representation(self, value):
        instance = self.root.instance
        # If the instance is a queryset, get the current instance from the queryset
        if issubclass(instance.__class__, (models.QuerySet, list)):
            instance = instance[self._call_count]
            self._call_count += 1
            
        instance_model_is_decorated = getattr(instance.__class__, "UTZMeta", None) and getattr(instance.__class__.UTZMeta, "_decorated", False)
        if not instance_model_is_decorated:
            raise ModelError(
                f"Model '{instance.__class__.__name__}', has not been decorated with a `ModelDecorator`"
            )
        
        user = get_user(instance)
        if user:
            self.timezone = user.utz
        return super().to_representation(value)
    

    def to_internal_value(self, value):
        if getattr(settings, "USE_DEPRACATED_PYTZ", False):
            server_timezone = pytz.timezone(settings.TIME_ZONE) if settings.USE_TZ else pytz.utc
        else:
            server_timezone = zoneinfo.ZoneInfo(settings.TIME_ZONE) if settings.USE_TZ else zoneinfo.ZoneInfo("UTC")
        return super().to_internal_value(value).astimezone(server_timezone)



class UTZDateTimeField(UTZField, serializers.DateTimeField):
    """
    Custom `serializers.DateTimeField` that converts input datetime to server's timezone(settings.TIMEZONE) before storage
    and converts back to the preferred user's local timezone on output.

    However, the model of the serializer in which this field is used must be decorated with a `ModelDecorator`.
    
    This field is usually added automatically to the model serializer if it is deorated with a `ModelSerializerDecorator`. 
    This can also work as a standalone field in a serializer without the decorator.

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
    pass
