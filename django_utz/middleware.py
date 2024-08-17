from django.utils.deprecation import MiddlewareMixin
import threading
from django.contrib.auth.models import AbstractUser, User, AbstractBaseUser
from typing import TypeVar, Optional

UserModel = TypeVar("UserModel", AbstractUser, User, AbstractBaseUser)

__local_thread_storage = threading.local()

REQUEST_USER_KEY = "DJANGO_UTZ:REQUEST_USER"


class DjangoUTZMiddleware(MiddlewareMixin):
    def process_request(self, request) -> None:
        """Stores the current authenticated user in the local thread storage."""
        if request.user.is_authenticated:
            setattr(__local_thread_storage, REQUEST_USER_KEY, request.user)
        else:
            setattr(__local_thread_storage, REQUEST_USER_KEY, None)

    def process_response(self, request, response):
        """
        Deletes the current authenticated user from the local thread storage.
        """
        if hasattr(__local_thread_storage, REQUEST_USER_KEY):
            delattr(__local_thread_storage, REQUEST_USER_KEY)
        return response


def get_request_user() -> Optional[UserModel]:
    """Returns the currently authenticated user. If no user is authenticated, returns None."""
    if hasattr(__local_thread_storage, REQUEST_USER_KEY):
        request_user = getattr(__local_thread_storage, REQUEST_USER_KEY)
        if request_user is not None and request_user.is_authenticated:
            return request_user
    return None
