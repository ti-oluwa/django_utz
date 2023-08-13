from rest_framework import serializers
from django.conf import settings
import pytz
from django.db import models

from ..models.mixins import UTZModelMixin, UTZUserModelMixin
from ..utils import get_attr_by_traversal


class UTZBaseField:
    """Base class for all UTZ fields"""

    _call_count = 0


    def get_utz(self, instance: UTZModelMixin | models.Model):
        """
        Return the user's timezone
        
        :param instance: The serializer model instance
        :type instance: subclass of UTZModelMixin
        """
        assert issubclass(instance.__class__, UTZModelMixin), (
            f'{self.__class__.__name__} requires the root model to inherit from '
            'UTZModelMixin'
        )
        user = instance
        if not instance.is_user_model:
            user_field_traversal_path = instance.find_user_related_model_field()
            user = get_attr_by_traversal(instance, user_field_traversal_path)
        assert issubclass(user.__class__, UTZUserModelMixin), (
            f'{self.__class__.__name__} requires the user model to inherit from '
            'UTZUserModelMixin'
        )
        timezone_name = user._utz_
        return pytz.timezone(timezone_name)


    def to_representation(self, value):
        instance = self.root.instance
        # If the instance is a queryset, get the current instance from the queryset
        if issubclass(instance.__class__, (models.QuerySet, list)):
            instance = instance[self._call_count]
            self._call_count += 1
        self.timezone = self.get_utz(instance=instance) # get the user timezone for the current instance
        return super().to_representation(value)
    

    def to_internal_value(self, value):
        server_timezone = pytz.timezone(settings.TIME_ZONE) if settings.USE_TZ else "UTC"
        return super().to_internal_value(value).astimezone(server_timezone)



class UTZTimeField(UTZBaseField, serializers.TimeField):
    """
    Custom `serializers.TimeField` that converts time to server's timezone(settings.TIMEZONE) before storage
    and converts back to user local timezone on representation. This is used by `UTZModelSerializerMixin` to automatically
    convert time fields to user's local timezone.

    It can also be used as a standalone field in a serializer without the `UTZModelSerializerMixin` mixin.

    if settings.USE_TZ is False, server's timezone is assumed to be UTC

    #### Example:
    ```python
    class BookSerializer(serializers.ModelSerializer):
        created_at_time = UTZTimeField(format="%H:%M:%S %Z (%z)")
        updated_at_time = UTZTimeField(format="%H:%M:%S %Z (%z)")

        class Meta:
            model = Book
            fields = "__all__"
            extra_kwargs = {
                "created_at_time": {"read_only": True},
                "updated_at_time": {"read_only": True},
            }
    ```
    """
    pass



class UTZDateTimeField(UTZBaseField, serializers.DateTimeField):
    """
    Custom `serializers.DateTimeField` that converts datetime to server's timezone(settings.TIMEZONE) before storage
    and converts back to user local timezone on representation. This is used by `UTZModelSerializerMixin` to automatically
    convert datetime fields to user's local timezone.

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