from django.core.exceptions import FieldError, ImproperlyConfigured, FieldDoesNotExist
import types
import pytz
import datetime
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, AbstractBaseUser, User
try:
    import zoneinfo
except:
    from backports import zoneinfo


from ..utils import is_timezone_valid, final, validate_timezone, get_attr_by_traversal
from ..middleware import get_request_user


user_models = (AbstractBaseUser, AbstractUser, User)



class UTZUserModelMixin:
    """
    ### This mixin must be used with the user model for the django-utz package to work properly.
    It adds necessary methods and properties to the User model to allow other mixins in this module to work.

    :attr user_timezone_field: The name of the field in the User model which stores the user's timezone. Defaults to None


    #### Below is an example usage of this mixin:
    ```
    from django.db import models
    from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
    from django_utz.models.mixins import UTZUserModelMixin

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

    user_timezone_field = None

    def __init__(self, *args, **kwargs):
        obj = super().__init__(*args, **kwargs)
        self._user_model_pre_check()
        return obj


    @property
    def utz(self):
        """
        The user's timezone info as a pytz.tzinfo or zoneinfo.ZoneInfo object.

        if settings.USE_DEPRECATED_PYTZ is True, then the user's timezone info is returned as a pytz.tzinfo object.
        Otherwise, it is returned as a zoneinfo.ZoneInfo object.

        if `user_timezone_field` is not set, then this returns settings.TIME_ZONE or UTC timezone
        """
        if self.user_timezone_field:
            try:
                utz = getattr(self, self.user_timezone_field)
            except AttributeError:
                raise FieldError(f"Field `{self.user_timezone_field}` does not exist in `{self.__class__.__name__}` model.\
                                Please add a `{self.user_timezone_field}` field in the model or set `user_timezone_field` attribute to the name of the field in `{self.__class__.__name__}` model which stores the user's timezone.")
            
            if utz and isinstance(utz, (pytz.BaseTzInfo, zoneinfo.ZoneInfo)):
                zone_str = utz.zone
            elif utz and isinstance(utz, str):
                if not is_timezone_valid(utz):
                    raise ValueError(f"Invalid timezone: {utz}.")
                zone_str = utz
            else:
                zone_str = getattr(settings, "TIMEZONE", None) or "UTC"

            if getattr(settings, "USE_DEPRECATED_PYTZ", False):
                return pytz.timezone(utz)
        else:
            zone_str = getattr(settings, "TIMEZONE", None) or "UTC"
        return zoneinfo.ZoneInfo(zone_str)


    @property
    def is_user_model(self):
        """Check if the model class which contains this mixin is the User model"""
        return issubclass(self.__class__, user_models)
    

    def _user_model_pre_check(self):
        """Ensures that the model in which this mixin is used is the User model"""
        if not self.is_user_model:
            raise TypeError("This mixin can only be used with the User model.")
        
        # Add user_timezone_field to the model if not already added
        if self.user_timezone_field and not hasattr(self, self.user_timezone_field):
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
    def to_local_timezone(self, _datetime: datetime.datetime):
        """
        Adjust datetime.datetime object to user's local timezone
        
        :param _datetime: datetime.datetime object
        :return: datetime object adjusted to user's timezone
        """
        if self.utz:
            local_time = _datetime.astimezone(self.utz)
            return self.utz.normalize(local_time)
        return _datetime



class UTZModelMixin:
    """
    ### Adds properties which return the values of the fields in the `datetime_fields` attribute in the preferred user's timezone.
    #### This properties are created dynamically and added to the model in which this mixin is used. 
    The property names are the field names in the `datetime_fields` attribute plus the suffix specified in the `utz_property_suffix` attribute.

    :attr datetime_fields: The datetime model fields for which the preferred user timezone properties are to be created.
    This fields should be in the model in which this mixin is used. Overriding this attribute is required.
    :attr utz_property_suffix: The suffix to be added to the preferred user timezone properties. Defaults to "utz".
    :attr use_related_user_timezone: If True, the mixin gets the user related to the model(as specified or automatically) and uses its timezone. 
    If False, the mixin uses the request user's timezone. Defaults to False.
    :attr related_user_field_path: The name/traversal path of the field in the model in which this mixin is used, that holds/returns the preferred user.
    :attr _model_superclass: The model superclass. Defaults to `models.Model`.

    #### For Example:
    ```
    # After `UTZUserModelMixin` has been added to the User model
    from django.contrib.auth import get_user_model
    from django_utz.models.mixins import UTZModelMixin

    User = get_user_model()

    class Book(UTZModelMixin, models.Model):
        title = models.CharField(...)
        content = models.TextField(...)
        author = models.ForeignKey(User, ...)
        created_at = models.DateTimeField(...)
        updated_at = models.DateTimeField(...)

        datetime_fields = ["created_at", "updated_at"]
        utz_property_suffix = "local" # defaults to "utz" which stands for "user timezone"
        use_related_user_timezone = False

    # Creating a book object
    book = Book.objects.create(...)
    print(book.created_at_local) # returns the value of `book.created_at` in the request user's timezone

    ```

    If we decide to use the related user timezone instead of the request user's timezone, 
    we can set `use_related_user_timezone` to True and set `related_user_field_path` 
    
    ```
    class Book(UTZModelMixin, models.Model):
        ...
        use_related_user_timezone = True
        related_user_field_path = "author" # The name of the field in the model which returns the preferred user
        
    # Creating a book object
    book = Book.objects.create(...)
    print(book.created_at_local) # returns the value of `book.created_at` in the book.author's timezone FOR ALL USERS
    """
    datetime_fields = []
    utz_property_suffix = "utz"
    use_related_user_timezone = False # If True, the mixin gets the related user object(as specified or automatically) and uses its timezone. If False, the mixin uses the request user's timezone
    related_user_field_path = None
    _model_superclass = models.Model


    def __init__(self, *args, **kwargs):
        obj = super().__init__(*args, **kwargs)
        self._model_pre_check()
        if self.user_available:
            self.create_and_add_utz_properties()
        return obj
    
    @property
    def is_user_model(self):
        """Check if the model class which contains this mixin is the User model"""
        return issubclass(self.__class__, user_models)

    @property
    def user_available(self):
        """Check if a user object whose timezone is to be used is available"""
        return self.get_preferred_user() is not None
    

    def _model_pre_check(self):
        """
        Check if model is properly setup
        """
        assert issubclass(self._model_superclass, models.Model), (
            f"Invalid superclass for model {self.__class__.__name__}: {self._model_superclass}."
        )
        if not self.is_user_model and not issubclass(self.__class__, self._model_superclass): # Check that the class inherits `self._model_superclass`
            raise ImproperlyConfigured(f"Model {self.__class__.__name__} does not inherit from {self._model_superclass.__name__}.")

        if not hasattr(self, "datetime_fields"):
            raise AttributeError(f"Model {self.__class__.__name__} does not have `datetime_fields` attribute.")
        return None
    
    
    def create_and_add_utz_properties(self):
        """
        Creates and adds local timezone properties for all fields in `self.datetime_fields`
        based on the preferred user's timezone.
        """
        assert type(self.datetime_fields) == list, (
            f"Invalid type for `datetime_fields`: {type(self.datetime_fields)}."
        )
        for datetime_field in self.datetime_fields:
            property = types.DynamicClassAttribute(fget=self.create_utz_method_for_datetime_field(datetime_field), \
                                                   doc=f"Returns the {datetime_field} in the user's timezone.")
            setattr(self.__class__, f"{datetime_field}_{self.utz_property_suffix}", property)
        return self


    def get_preferred_user(self):
        """
        Get and returns the user object whose timezone is to be used, based on the `related_user_field_path` attribute if set or
        the request user if `use_related_user_timezone` is False.
        
        If `use_related_user_timezone` is True and `related_user_field_path` is not set, then the mixin
        tries to find the user related field in the model and its related models and returns the first
        user object found.
        """
        user = self
        if not self.is_user_model: 
            if self.use_related_user_timezone:
                # Get the user object as specified by the `related_user_field_path` attribute or by finding the user related field in the model and its related models
                user_field_traversal_path = self.related_user_field_path or self.find_user_related_model_field()
                if not user_field_traversal_path:
                    if self.related_user_field_path:
                        raise ImproperlyConfigured(f"Please set `related_user_field_path` attribute to the name/traversal path of the field in {self.__class__.__name__} model which returns the preferred user.")
                    raise FieldError(f"No relation to the User model was found in {self.__class__.__name__}")
                
                user = get_attr_by_traversal(obj=self, traversal_path=user_field_traversal_path) # Get the user instance using its traversal path from this model
                if not isinstance(user, user_models):
                    raise FieldError(f"object of type {type(user)} from field: '{user_field_traversal_path}'; is not a User. If you provided a value for `related_user_field_path`, check that it points to a model field that returns the preferred user")
            else:
                user = get_request_user()
                
        if self.pk: # Only check if the model object has been saved
            self.check_user_has_utz_mixin(user)
        return user
    

    def create_utz_method_for_datetime_field(self, datetime_field: str):
        """
        Returns a method that would return the datetime model field's value in the user's timezone.

        :param datetime_field: The datetime model field for which the method is to be created.
        should already be in `self.datetime_fields`
        :raises ValueError: If the given datetime_field is not in `self.datetime_fields`
        """
        if datetime_field not in self.datetime_fields:
            raise ValueError(f"Invalid property name: {datetime_field}")
        
        utz_method = f"{datetime_field}_{self.utz_property_suffix}"
        user = self.get_preferred_user()

        def utz_method(self):
            return user.to_local_timezone(getattr(self, datetime_field))
        
        return utz_method
            
    
    @staticmethod
    def check_user_has_utz_mixin(user: AbstractBaseUser | AbstractUser):
        """
        Checks if the user model inherits the `UTZUserModelMixin` mixin.

        :param user: The user whose model is to be checked.
        """
        if not issubclass(user.__class__, UTZUserModelMixin):
            raise ImproperlyConfigured(f"{user.__class__.__name__} must inherit the `UTZUserModelMixin` mixin.")
        return True
  

    def find_user_related_model_field(self):
        """
        Finds and returns the traversal path to the first user related field found in the model or its related models.

        This method assumes that the user is a foreign key or one-to-one field in the model or its related models.

        :return: The user field traversal path or None if not found.
        """
        field_paths = []

        def find_user_related_field_path(model: models.Model):
            """Finds and returns the user related field traversal path in the given model or its related models."""
            for field in model._meta.fields:
                related_model = field.related_model
                if related_model and isinstance(field, (models.ForeignKey, models.OneToOneField)):
                    field_paths.append(field.name)
                    if issubclass(related_model, user_models):
                        return ".".join(field_paths)
                    else:
                        # if the field is a relational field but it is related_model is not the user model, 
                        # check the related_model's fields for the user related field
                        return find_user_related_field_path(model=related_model)  
            field_paths.pop()
            return None
                
        return find_user_related_field_path(model=self)

