
from .mixins import UTZModelMixin
from .fields import UTZDateTimeField, UTZTimeField



class UTZModelSerializerMixin:
    """
    #### A mixin that adds the fields defined in `self.Meta.model.time_related_fields` to the serializer as `UTZDateTimeField`s.

    :attr utz_repr_format: The format in which the datetime fields should be represented in the serializer.
    Defaults to `"%Y-%m-%d %H:%M:%S %Z (%z)"`.

    #### Example:
    ```
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

    utz_props_mixin = UTZModelMixin
    utz_repr_format = "%Y-%m-%d %H:%M:%S %Z (%z)"


    def __init__(self, *args, **kwargs):
        obj = super().__init__(*args, **kwargs)
        self._model_serializer_pre_check()
        self._add_utz_fields()
        return obj


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
        assert issubclass(self.utz_props_mixin, UTZModelMixin) == True,(
            f"Invalid `utz_props_mixin` value: {self.utz_props_mixin}."
        )
        if self.utz_props_mixin not in self.serializer_model.__bases__: # Check that the serializer class inherits `self.utz_props_mixin`
            raise NotImplementedError(f"Model {self.serializer_model.__name__} does not inherit from {self.utz_props_mixin.__name__}.")

        if not hasattr(self.serializer_model, "time_related_fields"):
            raise AttributeError(f"Model {self.serializer_model.__class__.__name__} does not have `time_related_fields` attribute.")
        return None
    

    def _add_utz_field_for(self, time_related_field: str):
        """
        Adds a `UTZDateTimeField` for the given time related field to the serializer.

        :param time_related_field: The time related field for which the `UTZDateTimeField` is to be added.
        should already be in `self.time_related_fields`
        """
        if time_related_field not in self.time_related_fields:
            raise ValueError(f"Invalid property name: {time_related_field}")
        
        if self.utz_props_mixin.is_datetime_field(time_related_field):
            self.fields[time_related_field] = UTZDateTimeField(format=self.utz_repr_format)
        elif self.utz_props_mixin.is_time_field(time_related_field):
            self.fields[time_related_field] = UTZTimeField(format=self.utz_repr_format)
        return None

    
    def _add_utz_fields(self):
        """
        Generates a `UTZDateTimeField` for all fields in `self.time_related_fields` 
        that returns fields value adjusted to `self.serializer_model` user's timezone.
        """
        assert type(self.time_related_fields) == list, (
            f"Invalid type for `time_related_fields`: {type(self.time_related_fields)}."
        )
        for time_related_field in self.time_related_fields:
            if time_related_field in self.Meta.fields or time_related_field not in self.Meta.exclude:
                self._add_utz_field_for(time_related_field)
        return self


