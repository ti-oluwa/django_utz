from django.utils.deprecation import MiddlewareMixin
import threading
from django.contrib.auth.models import AbstractUser, User, AbstractBaseUser
from typing import TypeVar, Optional

UserModel = TypeVar("UserModel", AbstractUser, User, AbstractBaseUser)

local_thread_storage = threading.local()


class DjangoUTZMiddleware(MiddlewareMixin):
    def process_request(self, request) -> None:
        """Stores the current authenticated user in the local thread storage."""
        if request.user.is_authenticated:
            setattr(local_thread_storage, "django_utz-request_user", request.user)
        else:
            setattr(local_thread_storage, "django_utz-request_user", None)

    def process_response(self, request, response):
        """
        Deletes the current authenticated user from the local thread storage.
        """
        if hasattr(local_thread_storage, "django_utz-request_user"):
            delattr(local_thread_storage, "django_utz-request_user")
        return response


def get_request_user() -> Optional[UserModel]:
    """Returns the currently authenticated user. If no user is authenticated, returns None."""
    if hasattr(local_thread_storage, "django_utz-request_user"):
        request_user = getattr(local_thread_storage, "django_utz-request_user")
        if request_user is not None and request_user.is_authenticated:
            return request_user
    return None
