"""Provides custom serializer fields for converting datetime to user's local timezone on representation"""
import zoneinfo
from rest_framework import serializers
from django.conf import settings
import pytz
from django.db import models

from django_utz.models.mixins import UTZModelMixin


class UTZBaseField:
    """Base class for UTZ fields"""

    _call_count = 0

    def to_representation(self, value):
        instance = self.root.instance
        # If the instance is a queryset, get the current instance from the queryset
        if issubclass(instance.__class__, (models.QuerySet, list)):
            instance = instance[self._call_count]
            self._call_count += 1
            
        assert issubclass(instance.__class__, UTZModelMixin), (
            f'{self.__class__.__name__} requires the {instance.__class__.__name__} model to inherit from '
            'UTZModelMixin'
        )
        if instance.user_available:
            self.timezone = instance.get_preferred_user().utz
        return super().to_representation(value)
    

    def to_internal_value(self, value):
        if getattr(settings, "USE_DEPRACATED_PYTZ", False):
            server_timezone = pytz.timezone(settings.TIME_ZONE) if settings.USE_TZ else pytz.utc
        else:
            server_timezone = zoneinfo.ZoneInfo(settings.TIME_ZONE) if settings.USE_TZ else zoneinfo.ZoneInfo("UTC")
        return super().to_internal_value(value).astimezone(server_timezone)


class UTZDateTimeField(UTZBaseField, serializers.DateTimeField):
    """
    Custom `serializers.DateTimeField` that converts input datetime to server's timezone(settings.TIMEZONE) before storage
    and converts back to the preferred user's local timezone on representation. 
    
    This field is usually added automatically to the model serializer by the `UTZModelSerializerMixin`. 
    It can also be used as a standalone field in a serializer without the `UTZModelSerializerMixin` mixin.

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