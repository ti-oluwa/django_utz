from django.core.exceptions import FieldError, ImproperlyConfigured, FieldDoesNotExist
import types
import pytz
import datetime
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, AbstractBaseUser, User


from ..utils import is_timezone_valid, final, validate_timezone, get_attr_by_traversal


user_models = (AbstractBaseUser, AbstractUser, User)



class UTZUserModelMixin:
    """
    ### This mixin is required to be used with the User model.
    It adds necessary methods and properties to the User model to allow other mixins in this module to work.

    :attr user_timezone_field: The name of the field in the User model which stores the user's timezone. Defaults to "timezone"


    #### Below is an example usage of this mixin:
    ```
    from django.db import models
    from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
    from django_utz_mixins.mixins import UTZUserModelMixin

    class User(UTZUserModelMixin, AbstractBaseUser, PermissionsMixin):
        '''User model'''
        username = models.CharField(max_length=255, unique=True)
        email = models.EmailField(max_length=255, unique=True)
        timezone = models.CharField(max_length=255, blank=True)
        ...

        USERNAME_FIELD = "email"
        REQUIRED_FIELDS = ["username"]

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
        return utz or settings.TIME_ZONE or "UTC"


    @property
    def is_user_model(self):
        """Check if the model in which this mixin is used is the User model"""
        return issubclass(self.__class__, user_models)
    

    def _model_pre_check(self):
        """Ensure that the model in which this mixin is used is the User model"""
        if not self.is_user_model:
            raise TypeError("This mixin can only be used with the User model.")
        
        # Add user_timezone_field to the model if not already added
        if not hasattr(self, self.user_timezone_field):
            raise ImproperlyConfigured(f"Field `{self.user_timezone_field}` does not exist in `{self.__class__.__name__}` model. Please add a `{self.user_timezone_field}` field in the model or set `user_timezone_field` attribute to the name of the field in `{self.__class__.__name__}` model which stores the user's timezone.")

        # Add timezone validator to the user_timezone_field if not already added
        try:
            field = self._meta.get_field(self.user_timezone_field)
            if field and validate_timezone not in field.validators:
                field.validators.append(validate_timezone)
        except FieldDoesNotExist:
            pass
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
    ### Adds properties which return the values of the fields in `self.time_related_fields` in the user's timezone.
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
    from django_utz_mixins.mixins import UTZModelMixin

    User = get_user_model()

    class Book(UTZModelMixin, models.Model):
        title = models.CharField(...)
        content = models.TextField(...)
        author = models.ForeignKey(User, ...)
        created_at = models.DateTimeField(...)
        updated_at = models.DateTimeField(...)

        time_related_fields = ["created_at", "updated_at"]
        utz_property_suffix = "local" # defaults to "utz" which stands for "user timezone"

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
        if not self.is_user_model and not issubclass(self.__class__, self._model_superclass): # Check that the class inherits `self._model_superclass`
            raise ImproperlyConfigured(f"Model {self.__class__.__name__} does not inherit from {self._model_superclass.__name__}.")

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
        Returns a method that would be convert to a property for the given time related field. 
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
            user_field_traversal_path = self.find_user_related_model_field()
            if not user_field_traversal_path:
                raise FieldError(f"No relation to the User model was found in {self.__class__.__name__}")
            user = get_attr_by_traversal(obj=self, traversal_path=user_field_traversal_path) # Get the user instance using its traversal path from this model
        
        if self.pk: # Only check if the model object has been saved
            self._check_user_model_has_utz_mixin(user)

        def utz_method(self):
            return user.to_local_timezone(getattr(self, time_related_field))
        
        return utz_method
            
    
    @staticmethod
    def _check_user_model_has_utz_mixin(user: AbstractBaseUser | AbstractUser):
        """
        Checks if the user model has the `UTZUserModelMixin` mixin or its subclass.

        :param user: The user whose model is to be checked.
        """
        if not issubclass(user.__class__, UTZUserModelMixin):
            raise ImproperlyConfigured(f"{user.__class__.__name__} must inherit the `UTZUserModelMixin` mixin.")
        return True
  

    def find_user_related_model_field(self):
        """
        Finds the user field in the model or its related models.

        :return: The user field traversal path or None if not found.
        """
        field_paths = []

        def find_user_related_field_path(model: models.Model):
            """Finds and returns the user related field traversal path in the given model or its related models."""
            for field in model._meta.fields:
                related_model = field.related_model
                if related_model:
                    field_paths.append(field.name)
                    if issubclass(related_model, user_models):
                        return ".".join(field_paths)
                    else:
                        # if the field is a relational field but it is related_model is not the user model, 
                        # check the related_model's fields for the user related field
                        return find_user_related_field_path(model=related_model)  
            field_paths.pop()
                
        return find_user_related_field_path(model=self)

