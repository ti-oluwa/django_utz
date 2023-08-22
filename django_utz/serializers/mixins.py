"""django_utz model serializers mixins"""

from typing import Dict
from django.core.exceptions import ImproperlyConfigured

from django_utz.models.mixins import UTZModelMixin
from django_utz.serializers.fields import UTZDateTimeField
from django_utz.utils import is_datetime_field


class UTZModelSerializerMixin:
    """
    ### Automatically adds the fields defined in `self.Meta.model.datetime_fields` to the serializer as `UTZDateTimeField`'s.

    NOTE: This mixin should only be used if the serializer model inherits `UTZModelMixin`. 
    Also, the auto added fields override already present fields with the same name in the serializer.
    To modify the behavior of the auto added fields using keyword arguments, 
    add the keyword arguments in the `extra_kwargs` attribute of the serializer's Meta class.

    If you need complete control of the field's behavior you should not use this mixin and instead add the fields manually to the serializer.

    ```
    from django_utz.serializers.fields import UTZDateTimeField

    class BookSerializer(serializers.ModelSerializer):
        ...
        # Display the `created_at` datetime field as time only in the user's timezone
        created_at_time = UTZDateTimeField(source=created_at, format="%H:%M:%S %Z (%z)", read_only=True)
        updated_at = UTZDateTimeField(format="%Y-%m-%d %H:%M:%S %Z (%z)", read_only=True)
        ...
    ```

    The default format in which the datetime fields are represented in the serializer is `"%Y-%m-%d %H:%M:%S %Z (%z)"`.
    This can be changed by setting the `datetime_repr_format` attribute in the serializer class.

    :attr datetime_repr_format: The format in which the datetime fields should be represented in the serializer.
    Defaults to `"%Y-%m-%d %H:%M:%S %Z (%z)"`.
    :attr add_utz_fields: If True, the fields defined in `self.Meta.model.datetime_fields` will be automatically added to the serializer as `UTZDateTimeField`'s.
    Defaults to True.

    #### Example:
    ```
    from django_utz.serializers.mixins import UTZModelSerializerMixin

    class BookSerializer(UTZModelSerializerMixin, serializers.ModelSerializer):
        datetime_repr_format = "%Y-%m-%d %H:%M:%S %Z"
        
        class Meta:
            model = Book
            fields = "__all__"
            extra_kwargs = {
                "created_at": {"read_only": True},
                "updated_at": {"read_only": True},
            }
    ```
    """
    utz_model_mixin = UTZModelMixin
    add_utz_fields = True
    datetime_repr_format = "%Y-%m-%d %H:%M:%S %Z (%z)"


    def __init__(self, *args, **kwargs):
        obj = super().__init__(*args, **kwargs)
        self._model_serializer_pre_check()
        return obj
    
    
    # Override `get_fields` method to add UTZ fields to the serializer
    def get_fields(self):
        fields = super().get_fields()
        if self.add_utz_fields:
            fields = self.get_and_add_utz_fields(fields)
        return fields


    @property
    def serializer_model(self):
        """
        Returns the serializer's model.

        :return: The serializer's model.
        :rtype: django.db.models.Model
        """
        return self.Meta.model
    

    def _model_serializer_pre_check(self):
        """
        Check if model serializer is properly setup
        """
        assert issubclass(self.utz_model_mixin, UTZModelMixin) == True,(
            f"Invalid `utz_model_mixin` value: {self.utz_model_mixin}."
        )
        if self.utz_model_mixin not in self.serializer_model.__bases__: # Check that the serializer class inherits `self.utz_model_mixin`
            raise ImproperlyConfigured(
                f"Model {self.serializer_model.__name__} does not inherit from {self.utz_model_mixin.__name__}."
            )

        if not hasattr(self.serializer_model, "datetime_fields"):
            raise AttributeError(
                f"Model {self.serializer_model.__class__.__name__} does not have `datetime_fields` attribute."
            )
        return None
    

    def get_utz_field_for_datetime_field(self, datetime_field: str):
        """
        Returns appropriate UTZ Serializer field for the given datetime field name.

        :param datetime_field: The datetime model field for which UTZ serializer field will be returned. Should already be in `self.datetime_fields`
        :return: django_utz.serializers.fields.UTZDateTimeField
        """
        if datetime_field not in self.serializer_model.datetime_fields:
            raise ValueError(f"Invalid property name: {datetime_field}")
        
        extra_kwargs = self.Meta.extra_kwargs.get(datetime_field, {}) # Get extra kwargs for the field if any
        if is_datetime_field(self.serializer_model, datetime_field):
            if "format" not in extra_kwargs:
                extra_kwargs.update({"format": self.datetime_repr_format}) 
            return UTZDateTimeField(**extra_kwargs)
        return None

    
    def get_and_add_utz_fields(self, serializer_fields: Dict):
        """
        Gets and adds to the serializer_fields, a `UTZDateTimeField` for all fields in `self.datetime_fields` 
        that returns fields value adjusted to `self.serializer_model` preferred user's timezone. 
        This overrides any fields already present in the serializer.

        :param serializer_fields: dictionary of fields already present in the serializer.
        :return: serializer_fields with `UTZDateTimeField` for all fields in `self.datetime_fields`.
        """
        assert type(self.serializer_model.datetime_fields) == list, (
            f"Invalid type for `datetime_fields`: {type(self.serializer_model.datetime_fields)}."
        )
        for datetime_field in self.serializer_model.datetime_fields:
            if (datetime_field in self.Meta.fields) or (datetime_field not in self.Meta.exclude):
                serializer_fields[datetime_field] = self.get_utz_field_for_datetime_field(datetime_field)
        return serializer_fields

