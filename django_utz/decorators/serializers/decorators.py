from rest_framework import serializers
from django.db import models
from typing import Any, Dict
import inspect
import datetime

from ..bases import UTZDecorator
from ..utils import transform_utz_decorator
from ..models.exceptions import ModelError
from .exceptions import SerializerConfigurationError
from ...serializer_fields import UTZDateTimeField



class ModelSerializerDecorator(UTZDecorator):
    """Decorator for `rest_framework.serializers.ModelSerializer` classes."""
    all_configs = ("auto_add_fields", "datetime_format")
    required_configs = ("auto_add_fields",)
    __slots__ = ("serializer",)

    def __init__(self, serializer: type[serializers.ModelSerializer]) -> None:
        self.serializer = self.check_model_serializer(serializer)
        super().__init__()


    @property
    def serializer_model(self) -> type[models.Model]:
        """
        Returns the serializer's model.
        """
        return self.serializer.Meta.model
    
    
    def __call__(self) -> type[models.Model]:
        prepared_serializer = self.prepare_serializer()
        if not issubclass(prepared_serializer, serializers.ModelSerializer):
            raise TypeError("prepare_serializer method must return a model serializer")
        return prepared_serializer
    

    def check_model_serializer(self, serializer: type[serializers.ModelSerializer]) -> type[serializers.ModelSerializer]:
        """
        Check if the model serializer is properly setup.

        :param serializer: The model serializer to check.
        :return: The model serializer if properly setup.
        """
        if not issubclass(serializer, serializers.ModelSerializer):
            raise TypeError(f"'{serializer.__name__}' is not a model serializer")
        
        model = serializer.Meta.model
        utz_meta = getattr(model, "UTZMeta", None)
        model_is_decorated = utz_meta and utz_meta._decorated and getattr(utz_meta, "datetime_fields", None)
        if not model_is_decorated:
            raise ModelError(
                f"Serializer's model {model.__name__}, has not been decorated with a `ModelDecorator`"
            )
        
        if not hasattr(serializer, "UTZMeta"):
            raise AttributeError("Model serializer must have a UTZMeta class")
        
        if not inspect.isclass(model.UTZMeta):
            raise SerializerConfigurationError("UTZMeta must be a class")
        
        for config in self.required_configs:
            if not getattr(serializer.UTZMeta, config, None):
                raise SerializerConfigurationError(f"'{config}' must be set in the model serializer's UTZMeta class")
        return serializer
    

    def validate_auto_add_fields(self, value: Any) -> None:
        if not isinstance(value, bool):
            raise SerializerConfigurationError("auto_add_fields must be a boolean")
        return None


    def validate_datetime_format(self, value: Any) -> None:
        if not isinstance(value, str):
            raise SerializerConfigurationError("datetime_format must be a string")

        try:
            datetime.datetime.now().strftime(value)
        except ValueError:
            raise SerializerConfigurationError(f"Invalid datetime format: {value}")
        return None


    def prepare_serializer(self) -> type[serializers.ModelSerializer]:
        """
        Prepare the serializer for use. This where you can customize the serializer.

        Here, user timezone aware datetime fields are automatically added to the serializer class.
        If `auto_add_fields` is set as True.
        """
        datetime_fields = self.serializer_model.UTZMeta.datetime_fields
        serializer_meta = self.serializer.Meta
        excluded_fields = serializer_meta.exclude if hasattr(serializer_meta, "exclude") else []
        included_fields = serializer_meta.fields if hasattr(serializer_meta, "fields") else []

        if included_fields == "__all__":
            included_fields = self.serializer_model._meta.fields

        # If the serializer has no fields, return it as is
        if not included_fields:
            return self.serializer

        if self.get_config("auto_add_fields"):
            for fieldname in datetime_fields:
                # Skip fields that are not included in the serializer
                if fieldname not in included_fields or fieldname in excluded_fields:
                    continue
                # If field is already defined in the serializer, skip it
                if hasattr(self.serializer, fieldname):
                    continue
                utz_datetime_field = self.get_utzdatetimefield_for_field(fieldname)
                setattr(self.serializer, fieldname, utz_datetime_field)
        return self.serializer
    

    def get_utzdatetimefield_for_field(self, datetime_field: str, serializer_meta: type[object]) -> UTZDateTimeField:
        """
        Returns a `UTZDateTimeField` for the given datetime field name in a serializer.

        :param datetime_field: The name of the datetime model field for which a `UTZDateTimeField` will be returned. 
        :param serializer_meta: The model serializer's meta class.
        :return: a `django_utz.serializer_fields.UTZDateTimeField` for the given datetime field.
        """
        meta_extra_kwargs: Dict = serializer_meta.extra_kwargs if hasattr(serializer_meta, "extra_kwargs") else {}
        field_extra_kwargs: Dict = meta_extra_kwargs.get(datetime_field, {}) # Get extra kwargs for the field if any

        datetime_format = self.get_config("datetime_format")
        if "format" not in field_extra_kwargs and datetime_format:
            field_extra_kwargs.update({"format": datetime_format}) 
        return UTZDateTimeField(**field_extra_kwargs)


    def set_config(self, attr: str, value: Any) -> None:
        """
        Sets a configuration attribute on the serializer.

        :param attr: The attribute to set.
        :param value: The value to set.
        """
        if not hasattr(self, "serializer"):
            raise AttributeError("Serializer not set")
        
        if attr != "_decorated" and attr not in self.all_configs:
            raise SerializerConfigurationError(f"Invalid config: {attr}")
        
        if value is not None and hasattr(self, f"validate_{attr}"):
            getattr(self, f"validate_{attr}")(value)

        setattr(self.serializer.UTZMeta, attr, value)
        return None


    def get_config(self, attr: str, default: Any = None) -> Any | None:
        """
        Gets a configuration attribute from the serializer.

        :param attr: The attribute to get.
        :param default: The default value to return if the attribute is not set.
        :return: The value of the attribute.
        """
        if not hasattr(self, "serializer"):
            raise AttributeError("Serializer not set")
        
        val = getattr(self.serializer.UTZMeta, attr, default)
        if val is not None and hasattr(self, f"validate_{attr}"):
            getattr(self, f"validate_{attr}")(val)
        return val


# Funtion-type decorator for `rest_framework.serializers.ModelSerializer` classes

def modelserializer(serializer: type[serializers.ModelSerializer]) -> type[serializers.ModelSerializer]:
    """
    #### `django_utz` decorator for `reest_framework.serializers.ModelSerializer` classes.

    This decorator auto adds user timezone aware datetime fields to the serializer class 
    in-place of the normal datetime fields, if `auto_add_fields` config is set as True.

    The decorated model serializer must have a `UTZMeta` class with the following attributes:
    - `auto_add_fields`: Optional. A boolean that determines if user timezone aware datetime fields should be automatically added to the serializer.
    - `datetime_format`: Optional. A string that determines the output format for the user timezone aware datetime fields.

    Example Usage:
    ```python
    from rest_framework import serializers
    from django_utz.decorators import modelserializer

    from .models import Article

    @modelserializer
    class ArticleSerializer(serializers.ModelSerializer):
        class Meta:
            model = Article
            fields = "__all__"
            exclude = ("updated_at",)
            extra_kwargs = {
                "published_at": {"read_only": True},
            }

        class UTZMeta:
            auto_add_fields = True
            datetime_format = "%Y-%m-%d %H:%M:%S"
    ```
    """
    return transform_utz_decorator(ModelSerializerDecorator)(serializer)
