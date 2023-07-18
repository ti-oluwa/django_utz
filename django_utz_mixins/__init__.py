"""
#### Django UTZ(User TimeZone) Mixins

This package contains mixins for Django models and DRF model serializers that helps you to easily convert time related fields to the user's timezone.

@Author: Daniel T. Afolayan (ti-oluwa.github.io)
"""

__all__ = [
    "UTZModelMixin",
    "UTZModelSerializerMixin",
    "UTZUserModelMixin",
    "UTZBaseField",
    "UTZTimeField",
    "UTZDateTimeField",
    "user_timezone_changed",
]

__version__ = "0.1.0"
__author__ = "Daniel T. Afolayan"
