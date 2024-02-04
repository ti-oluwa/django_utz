from django.db import models
import pytz
import datetime
from django.db import models
from django.conf import settings

try:
    import zoneinfo
except:
    from backports import zoneinfo
from django.contrib.auth.models import AbstractUser, AbstractBaseUser, User
from typing import TypeVar, List
from django.core.exceptions import FieldDoesNotExist
from typing import Callable


from ..utils import is_datetime_field, is_timezone_valid, validate_timezone, transform_utz_decorator
from ...datetime import utzdatetime
from .exceptions import ModelError, ModelConfigurationError
from .bases import ModelDecorator
from .utils import get_user, is_user_model, FunctionAttribute



class UserModelUTZMixin:
    """Adds neccessary methods and properties to the User Model"""
    
    @property
    def utz(self):
        """
        The user's timezone info as a `pytz.tzinfo` or `zoneinfo.ZoneInfo` object.

        if settings.USE_DEPRECATED_PYTZ is True, then the user's timezone info is returned as a pytz.tzinfo object.
        Otherwise, it is returned as a zoneinfo.ZoneInfo object.
        """
        utz = getattr(self, self.UTZMeta.timezone_field)
        
        if utz and isinstance(utz, datetime.tzinfo):
            zone_str = str(utz)

        elif utz and isinstance(utz, str):
            if not is_timezone_valid(utz):
                raise ValueError(f"Invalid timezone: {utz}.")
            zone_str = utz

        if getattr(settings, "USE_DEPRECATED_PYTZ", False):
            return pytz.timezone(zone_str)

        return zoneinfo.ZoneInfo(zone_str)


    def to_local_timezone(self, _datetime: datetime.datetime) -> utzdatetime:
        """
        Adjust datetime.datetime object to user's local timezone.
        If the user's timezone is not set, the datetime object is returned as is.
        
        :param _datetime: `datetime.datetime` object
        :return: `utzdatetime` object

        datetime object returned is not affected by `settings.USE_TZ`.
        To change this behavior do:
        ```
        import datetime
        utz_datetime = user.to_local_timezone(datetime.datetime.now())
        utz_datetime.regard_usetz()
        ```
        """
        utz_dt = utzdatetime.from_datetime(_datetime)
        user_tz = self.utz
        if user_tz:
            return utz_dt.astimezone(user_tz)
        return utz_dt


UserModel = TypeVar("UserModel", AbstractBaseUser, AbstractUser, User)
UTZUserModel = TypeVar("UTZUserModel", AbstractBaseUser, AbstractUser, User, UserModelUTZMixin)


class UserModelDecorator(ModelDecorator):
    """`ModelDecorator` for the project's user model."""
    all_configs = ("timezone_field",)
    required_configs = ("timezone_field",)

    def __init__(self, model: UserModel) -> None:
        super().__init__(model)


    def check_model(self, model: UserModel) -> UserModel:
        """Ensures that the model in which this mixin is used is the project's user model"""
        if not is_user_model(model):
            raise ModelError(f"Model '{model.__name__}' is not the project's user model")  
        return super().check_model(model)
    

    def validate_timezone_field(self, value: str) -> None:
        if not isinstance(value, str):
            raise ModelConfigurationError("Value for 'timezone_field' should be of type str")
        return None


    def prepare_model(self) -> UTZUserModel:
        # Add timezone validator to the `timezone_field`` if not already added
        try:
            timezone_field = self.get_config("timezone_field")
            field = self.model._meta.get_field(timezone_field)
            if field and validate_timezone not in field.validators:
                field.validators = [*field.validators, validate_timezone]
        except FieldDoesNotExist:
            raise ModelError(f"Field '{timezone_field}' does not exist in model '{self.model.__name__}'")
        
        self.model.__bases__ = (UserModelUTZMixin, *self.model.__bases__)
        return self.model



class RegularModelDecorator(ModelDecorator):
    """`ModelDecorator` for regular Django models."""
    all_configs = ("datetime_fields", "attribute_suffix", "use_related_user_timezone", "related_user")
    required_configs = ("datetime_fields",)

    def check_model(self, model: models.Model) -> models.Model:
        model = super().check_model(model)

        related_user = getattr(model.UTZMeta, "related_user", None)
        if related_user and not isinstance(related_user, str):
            raise ModelConfigurationError("'related_user' should be of type str")
        return model
    

    def prepare_model(self) -> type[models.Model]:
        if self.get_config("datetime_fields") == "__all__":
            self.set_config("datetime_fields", self.get_datetime_fields(self.model))

        if not self.get_config("attribute_suffix"):
            self.set_config("attribute_suffix", "utz")

        if not self.get_config("use_related_user_timezone"):
            self.set_config("use_related_user_timezone", False)

        return self.update_model_attrs(self.model)
    

    def validate_datetime_fields(self, value: str | List[str] | tuple[str]) -> None:
        if value != "__all__" and not isinstance(value, (list, tuple)):
            raise ModelConfigurationError(
                f"'datetime_fields' should be a list, tuple or '__all__'"
            )
        return None
    

    def validate_attribute_suffix(self, value: str) -> None:
        if not isinstance(value, str):
            raise ModelConfigurationError("'attribute_suffix' should be of type str")
        return None
    

    def validate_use_related_user_timezone(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ModelConfigurationError("'use_related_user_timezone' should be of type bool")
        return None
    

    def get_datetime_fields(self, model: type[models.Model]) -> List[str]:
        """Returns the datetime fields in the given model."""
        return [field.name for field in model._meta.fields if isinstance(field, models.DateTimeField)]
    

    def make_func_for_field(self, datetime_field: str) -> Callable[[models.Model], utzdatetime]:
        """
        Makes and returns a function that returns the value of the datetime field on a model instance
        in the user's local timezone.

        :param datetime_field: The name of the datetime field for which to make the function
        """
        func_name = f"get_{datetime_field}_{self.get_config("attribute_suffix")}"

        def func(model_instance: models.Model) -> utzdatetime:
            user: UserModel = get_user(model_instance)
            if user is None:
                return utzdatetime.from_datetime(getattr(model_instance, datetime_field))
            return user.to_local_timezone(getattr(model_instance, datetime_field))
        
        func.__name__ = func_name
        func.__qualname__ = func_name
        return func
            

    def update_model_attrs(self, model: type[models.Model]) -> type[models.Model]:
        """
        Updates the model with the read-only attributes for the datetime fields.

        :param model: The model to update
        """
        datetime_fields: List[str] = self.get_config("datetime_fields")
        attribute_suffix: str = self.get_config("attribute_suffix")

        for field in datetime_fields:
            if not is_datetime_field(model, field):
                raise ModelConfigurationError(f"Field '{field}' is not a datetime field in model '{model.__name__}'")
            
            func = self.make_func_for_field(field)
            read_only_attr = FunctionAttribute(func)
            attr_name = f"{field}_{attribute_suffix}"
            setattr(model, attr_name, read_only_attr)
        return model



# Function-type decorator for django models

def model(model: type[models.Model]) -> type[models.Model]:
    """
    #### `django_utz` decorator for django models.

    The decorated model must have a `UTZMeta` class with the following attributes:
    - `datetime_fields`: A list of the names of the datetime fields in the model or "__all__" to use all datetime fields.
    - `attribute_suffix`: Optional. The suffix to be added to the read-only attributes for utz versions  the datetime fields.
    Defaults to "utz".
    - `use_related_user_timezone`: Optional. A boolean indicating whether to use the timezone of the related user model.
    Defaults to False.
    - `related_user`: Optional. The name of the related user model if `use_related_user_timezone` is True.

    Example Usage:
    ```
    from django.db import models
    from django_utz.decorators import model

    @model
    class Article(models.Model):
        title = models.CharField(max_length=100)
        content = models.TextField()
        author = models.ForeignKey("Author", on_delete=models.CASCADE)
        published_at = models.DateTimeField()
        updated_at = models.DateTimeField()

        class UTZMeta:
            datetime_fields = ("published_at", "updated_at")
            attribute_suffix = "local"
    ```
    """
    return transform_utz_decorator(RegularModelDecorator)(model)



def usermodel(model: UserModel) -> UTZUserModel:
    """
    #### `django_utz` decorator for the project's user model.

    The user model must be decorated with this decorator for `django_utz` to work properly.
    The decorated model must have a `UTZMeta` class with the following attributes:
    - `timezone_field`: The name of the timezone field in the model.

    Example Usage:
    ```
    from django.contrib.auth.models import AbstractUser
    from django_utz.decorators import usermodel

    @usermodel
    class User(AbstractUser):
        id = models.AutoField(primary_key=True)
        email = models.EmailField(unique=True)
        username = models.CharField(max_length=100)
        ...
        timezone = models.CharField(max_length=100)

        class UTZMeta:
            timezone_field = "timezone"
    ```
    """
    return transform_utz_decorator(UserModelDecorator)(model)
