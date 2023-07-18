from django.core.exceptions import FieldError
import types
import pytz
import datetime
from django.db import models
from django.contrib.auth.models import AbstractUser, AbstractBaseUser, User


from .utils import is_timezone_valid, final


user_models = (AbstractBaseUser, AbstractUser, User)



class UTZUserModelMixin:
    """
    This mixin is required to be used with the User model.
    It adds necessary methods and properties to the User model to allow other mixins in this module to work.

    :attr user_timezone_field: The name of the field in the User model which stores the user's timezone. Defaults to "timezone"


    #### Below is an example usage of this mixin:
    ```
    from django.db import models
    from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
    from api.mixins import UTZUserModelMixin

    class User(UTZUserModelMixin, AbstractBaseUser, PermissionsMixin):
        '''User model'''
        username = models.CharField(max_length=255, unique=True)
        email = models.EmailField(max_length=255, unique=True)
        timezone = models.CharField(max_length=255, blank=True, null=True)
        is_staff = models.BooleanField(default=False)
        is_active = models.BooleanField(default=True)
        is_superuser = models.BooleanField(default=False)
        date_joined = models.DateTimeField(auto_now_add=True)
        last_login = models.DateTimeField(auto_now=True)

        USERNAME_FIELD = "email"
        REQUIRED_FIELDS = ["username"]

        time_related_fields = ["date_joined", "last_login"]
        user_timezone_field = "timezone" # valid user timezone info field name


    ```
    """

    user_timezone_field = "timezone"

    def __init__(self, *args, **kwargs):
        obj = super().__init__(*args, **kwargs)
        self._model_pre_check()
        return obj
    

    @property
    def _utz_(self):
        """The user's timezone"""
        utz = getattr(self, self.user_timezone_field, None)
        if utz is None:
            raise FieldError(f"Field `{self.user_timezone_field}` does not exist in `{self.__class__.__name__}` model. Please add a `{self.user_timezone_field}` field in the model or set `user_timezone_field` attribute to the name of the field in `{self.__class__.__name__}` model which stores the user's timezone.")
        if utz and not is_timezone_valid(utz):  # If timezone is invalid
            raise ValueError("Invalid timezone.")
        return utz


    @property
    def is_user_model(self):
        """Check if the model in which this mixin is used is the User model"""
        return issubclass(self.__class__, user_models)
    

    def _model_pre_check(self):
        """Ensure that the model in which this mixin is used is the User model"""
        if not self.is_user_model:
            raise TypeError("This mixin can only be used with the User model.")
        return None 
    
    @final
    def to_local_timezone(self, time: datetime.datetime):
        """
        Adjust time to user's local timezone
        
        :param time: datetime object
        :return: datetime object adjusted to user's timezone
        """
        if self._utz_:
            local_time = time.astimezone(pytz.timezone(self._utz_))
            return local_time
        return time



class UTZModelMixin:
    """
    #### Model Mixin to add properties which return the values of the fields in `self.time_related_fields` in the user's timezone.
    #### This properties are created dynamically and added to the model in which this mixin is used. 
    The property names are the field names in `self.time_related_fields` with the suffix `self.utz_property_suffix` added to them.

    :attr time_related_fields: The time related fields for which the user timezone properties are to be created.
    This fields should be in the model in which this mixin is used. Overriding this attribute is required.
    :attr utz_property_suffix: The suffix to be added to the user timezone properties. Defaults to "utz".
    :attr _model_superclass: The model superclass. Defaults to `models.Model`.

    NOTE: If the model in which this mixin is used is not the User model then the mixin assumes that the user object is any
    field associated with the User model.

    #### For Example:
    ```
    # After `UTZUserModelMixin` has been added to the User model
    from django.contrib.auth import get_user_model

    User = get_user_model()

    class Book(UTZModelMixin, models.Model):
        title = models.CharField(...)
        content = models.TextField(...)
        author = models.ForeignKey(User, ...)
        created_at = models.DateTimeField(...)
        updated_at = models.DateTimeField(...)

        time_related_fields = ["created_at", "updated_at"]
        utz_property_suffix = "local" # defaults to "utz" which stands for user timezone

    # Creating a book object
    book = Book.objects.create(...)
    print(book.created_at_local) # returns the value of `book.created_at` in the user's timezone

    ```
    Here the mixin assumes the field `author` holds user object and uses it's value's(the user object) timezone

    """

    time_related_fields = []
    utz_property_suffix = "utz"
    _model_superclass = models.Model


    def __init__(self, *args, **kwargs):
        obj = super().__init__(*args, **kwargs)
        self._model_pre_check()
        self._generate_utz_properties()
        return obj
    
    @property
    def is_user_model(self):
        """Check if the model in which this mixin is used is the User model"""
        return issubclass(self.__class__, user_models)

    
    def _model_pre_check(self):
        """
        Check if model is properly setup
        """
        assert issubclass(self._model_superclass, models.Model), (
            f"Invalid superclass for model {self.__class__.__name__}: {self._model_superclass}."
        )
        if self._model_superclass not in self.__class__.__bases__: # Check that the class inherits `self._model_superclass`
            raise NotImplementedError(f"Model {self.__class__.__name__} does not inherit from {self._model_superclass.__class__.__name__}.")

        if not hasattr(self, "time_related_fields"):
            raise AttributeError(f"Model {self.__class__.__name__} does not have `time_related_fields` attribute.")
        return None
    
    
    def _generate_utz_properties(self):
        """
        Generates local timezone properties for all fields in `self.time_related_fields`
        based on the user's timezone.
        """
        assert type(self.time_related_fields) == list, (
            f"Invalid type for `time_related_fields`: {type(self.time_related_fields)}."
        )
        for time_related_field in self.time_related_fields:
            property = types.DynamicClassAttribute(fget=self._create_utz_method_for(time_related_field), \
                                                   doc=f"Returns the {time_related_field} in the user's timezone.")
            setattr(self.__class__, f"{time_related_field}_{self.utz_property_suffix}", property)
        return self
    

    def _create_utz_method_for(self, time_related_field: str):
        """
        Returns a method that would be convert to a propety for the given time related field. 
        This method returns the time related field's value in the user's timezone.

        :param time_related_field: The time related field for which the property is to be created.
        should already be in `self.time_related_fields`
        :raises ValueError: If the given time_related_field is not in `self.time_related_fields`
        """
        if time_related_field not in self.time_related_fields:
            raise ValueError(f"Invalid property name: {time_related_field}")
        
        utz_method = f"{time_related_field}_{self.utz_property_suffix}"
        user = self
        if not self.is_user_model: # If the model is not the User model or its subclass, find the user related model field
            user_field = self._find_user_related_model_field()
            if user_field is None:
                raise FieldError(f"User related model field not found in {self.__class__.__name__}")
            user = getattr(self, user_field) # Get the user instance from the user related model field
        self._check_user_model_has_utz_mixin(user)

        def utz_method(self):
            return user.to_local_timezone(getattr(self, time_related_field))
        
        return utz_method
    
    @staticmethod
    def _check_user_model_has_utz_mixin(user_model: AbstractBaseUser | AbstractUser):
        """
        Checks if the user model has the `UTZUserModelMixin` mixin or its subclass.
        """
        if not issubclass(user_model.__class__, UTZUserModelMixin):
            raise NotImplementedError(f"{user_model.__class__.__name__} must inherit the `UTZUserModelMixin` mixin.")
        return True
  

    def _find_user_related_model_field(self):
        """
        Finds the user field in the model.

        :return: The user field name in the model or None if not found.
        """
        for field in self._meta.fields:
            related_model = field.related_model
            if related_model and issubclass(related_model, user_models):
                return field.name
        return None


    def is_datetime_field(self, time_related_field: str):
        """
        Checks if the given field is a date time field in the model.

        :param time_related_field: The time related field to check.
        """
        field = self._meta.get_field(time_related_field)
        return isinstance(field, models.DateTimeField)
    

    def is_time_field(self, time_related_field: str):
        """
        Checks if the given field is a time field in the model.

        :param time_related_field: The time related field to check.
        """
        field = self._meta.get_field(time_related_field)
        return isinstance(field, models.TimeField)



