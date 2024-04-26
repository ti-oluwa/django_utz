from typing import Callable, List, Any
from django.db import models
from django.conf import settings

from ..utils import get_attr_by_traversal
from ...middleware import get_request_user
from .exceptions import ModelError, ModelConfigurationError


def get_model_traversal_path(model: type[models.Model]) -> str:
    """Returns the traversal path to the model."""
    return f"{model.__module__}.{model.__name__}"


def get_project_user_model() -> str:
    """Returns the traversal path to the project's user model."""
    auth_user_model: str = settings.AUTH_USER_MODEL
    split = auth_user_model.split('.', maxsplit=1)
    split.insert(1, "models")
    user_model_path = ".".join(split)
    return user_model_path


def is_user_model(model: type[models.Model]) -> bool:
    """Check if the model is the project's user model."""
    return get_project_user_model() == get_model_traversal_path(model)


class FunctionAttribute:
    """
    A descriptor class that returns the result of 
    passing an object into a function as an attribute.
    """
    def __init__(self, func: Callable[..., Any]):
        if not callable(func):
            raise TypeError("Value must be a function.")
        self.func = func


    def __set_name__(self, objtype, name: str):
        if not isinstance(name, str):
            raise TypeError('name must be a string')
        self.name = name


    def __get__(self, obj, objtype):
        return self.func(obj)


def get_user(model_obj: models.Model) -> models.Model | None:
    """
    Gets and returns the user object whose timezone is to be used by the model instance.
    
    If  the `use_related_user_timezone` config is True and `related_user` is not set, the first
    user object found that is related to the model instance is returned.

    If the user has still not been found, the request user is returned.

    :param model_obj: The model instance for which a user object is to be found.
    :return: The user object.
    :raises ModelError: If the user's model is not decorated with a `ModelDecorator`.
    """
    # Initially, assume that the object passed is a user object.
    user = model_obj
    model_obj_cls = model_obj.__class__
    if not is_user_model(model_obj_cls):
        if model_obj_cls.UTZMeta.use_related_user_timezone:
            # Get the user object as specified by the `related_user` config 
            # or by finding the user field in the model and its related models
            related_user = getattr(model_obj_cls.UTZMeta, "related_user", None) or find_user_field(model_obj_cls)
            if not related_user:
                if getattr(model_obj_cls.UTZMeta, "related_user", None):
                    raise ModelConfigurationError(
                        f"Make sure to set the `related_user` config to the name or traversal path of the user field in {model_obj_cls.__name__}."
                    )
                raise ModelError(f"No relation to the User model was found in {model_obj_cls.__name__}")
            
            user = get_attr_by_traversal(obj=model_obj, traversal_path=related_user)

        else:
            user = get_request_user()
            
    if user:
        user_model_is_decorated = getattr(user.__class__, "UTZMeta", None) and getattr(user.__class__.UTZMeta, "_decorated", False)
        if not user_model_is_decorated:
            raise ModelError(
                f"Model '{user.__class__.__name__}', has not been decorated with a `ModelDecorator`"
            )
    return user


def find_user_field(model: type[models.Model]) -> str | None:
    """
    Finds and returns the traversal path to the first user field found
    in the model or its related models.

    This method assumes that the user is a foreign key or one-to-one field.
    """
    field_paths = []
    
    def find_user_related_field(model: type[models.Model]) -> str | None:
        """
        Finds and returns the user related field traversal path 
        in the given model or its related models.
        """
        # First check all the fields in the model for the user field
        # If the user field is found, return the field path (Surface-level search)
        for field in model._meta.fields:
            if not is_user_model(field.related_model):
                continue
            field_paths.append(field.name)
            return ".".join(field_paths)

        # If the user field was not found at surface level, check each field's related model (if any).
        for field in model._meta.fields:
            related_model = field.related_model
            if related_model and isinstance(field, (models.ForeignKey, models.OneToOneField)):
                field_paths.append(field.name)

                if is_user_model(related_model):
                    return ".".join(field_paths)
                else:
                    # If the field is not the user field, recursively check the field's 
                    # related model for the user field, both at surface level and in its related models (if any).
                    return find_user_related_field(related_model) 
                
        # If the user field was not found in the model or its related models, pop the last field path and return. 
        if field_paths:
            field_paths.pop()
        return
         
    return find_user_related_field(model)


def get_datetime_fields(self, model: type[models.Model]) -> List[str]:
    """Returns a list of the datetime fields in the given model."""
    return [field.name for field in model._meta.fields if isinstance(field, models.DateTimeField)]
