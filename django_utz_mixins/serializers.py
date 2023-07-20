from typing import Dict
from django.core.exceptions import ImproperlyConfigured

from .mixins import UTZModelMixin
from .fields import UTZDateTimeField, UTZTimeField



class UTZModelSerializerMixin:
    """
    ### Automatically adds the fields defined in `self.Meta.model.time_related_fields` to the serializer as `UTZTimeField`s or `UTZDateTimeField`s.

    NOTE: This mixin should only be used if the serializer model inherits `UTZModelMixin`. Also, the auto added fields override fields with the same name in the serializer.
    To modify the behavior of the auto added fields using keyword arguments, add the keyword arguments in the `extra_kwargs` attribute of the serializer's Meta class.

    If you need complete control of the field's behavior you should not use this mixin and instead add the fields manually to the serializer.

    ```
    from django_utz_mixins.fields import UTZDateTimeField, UTZTimeField

    class BookSerializer(serializers.ModelSerializer):
        created_at_time = UTZTimeField(format="%H:%M:%S %Z (%z)", read_only=True)
        updated_at = UTZDateTimeField(format="%Y-%m-%d %H:%M:%S %Z (%z)", read_only=True)
        ...
    ```

    The default format in which the datetime fields are represented in the serializer is `"%Y-%m-%d %H:%M:%S %Z (%z)"`.
    This can be changed by setting the `datetime_repr_format` attribute in the serializer class.
    Also the default format in which the time fields are represented in the serializer is `"%H:%M:%S %Z (%z)"`.
    This can be changed by setting the `time_repr_format` attribute in the serializer class.

    :attr utz_repr_format: The format in which the datetime fields should be represented in the serializer.
    Defaults to `"%Y-%m-%d %H:%M:%S %Z (%z)"`.

    #### Example:
    ```
    from django_utz_mixins.serializers import UTZModelSerializerMixin

    class BookSerializer(UTZModelSerializerMixin, serializers.ModelSerializer):
        utz_repr_format = "%Y-%m-%d %H:%M:%S %Z (%z)"
        
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
    datetime_repr_format = "%Y-%m-%d %H:%M:%S %Z (%z)"
    time_repr_format = "%H:%M:%S %Z (%z)"


    def __init__(self, *args, **kwargs):
        obj = super().__init__(*args, **kwargs)
        self._model_serializer_pre_check()
        return obj
    
    
    # Override `get_fields` method to add UTZ fields to the serializer
    def get_fields(self):
        fields = super().get_fields()
        fields = self._add_utz_fields(fields)
        return fields


    @property
    def time_related_fields(self):
        """
        Returns the time related fields in the serializer's model.

        :return: The time related fields in the self.Meta.model.
        :rtype: list
        """
        return self.serializer_model.time_related_fields
    

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
            raise ImproperlyConfigured(f"Model {self.serializer_model.__name__} does not inherit from {self.utz_model_mixin.__name__}.")

        if not hasattr(self.serializer_model, "time_related_fields"):
            raise AttributeError(f"Model {self.serializer_model.__class__.__name__} does not have `time_related_fields` attribute.")
        return None
    

    def _get_utz_field_for(self, time_related_field: str):
        """
        Returns appropriate UTZ field for the given time related field to the serializer.

        :param time_related_field: The time related field for which field will be returned. Should already be in `self.time_related_fields`
        :return: UTZTimeField or UTZDateTimeField depending on the type of the time_related_field. Whether its a time or datetime field.
        """
        if time_related_field not in self.time_related_fields:
            raise ValueError(f"Invalid property name: {time_related_field}")
        
        kwargs = self.Meta.extra_kwargs.get(time_related_field, {}) # Get extra kwargs for the field if any
        if self.serializer_model.is_datetime_field(time_related_field):
            return UTZDateTimeField(format=self.datetime_repr_format, **kwargs)
            
        elif self.serializer_model.is_time_field(time_related_field):
            return UTZTimeField(format=self.time_repr_format, **kwargs)
        return None

    
    def _add_utz_fields(self, serializer_fields: Dict):
        """
        Generates and adds to the serializer_fields, a `UTZDateTimeField`  or `UTZTimeField` for all fields in `self.time_related_fields` 
        that returns fields value adjusted to `self.serializer_model` user's timezone. This overrides any fields already present in the serializer.

        :param serializer_fields: dictionary of fields already present in the serializer.
        :return: serializer_fields with `UTZDateTimeField` or `UTZTimeField` for all fields in `self.time_related_fields`.
        """
        assert type(self.time_related_fields) == list, (
            f"Invalid type for `time_related_fields`: {type(self.time_related_fields)}."
        )
        for time_related_field in self.time_related_fields:
            if time_related_field in self.Meta.fields or time_related_field not in self.Meta.exclude:
                serializer_fields[time_related_field] = self._get_utz_field_for(time_related_field)
        return serializer_fields

