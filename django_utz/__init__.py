"""
#### django_utz

Decorators for Django models and DRF model serializers, custom serializer fields, 
template tags and filters that aid easy conversion of timezone aware fields to a user's timezone.

@Author: Daniel T. Afolayan (ti-oluwa.github.io)
"""

__version__ = "0.1.7"
__author__ = "Daniel T. Afolayan"

alias = "django-user-timezone"

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo
except:
    raise Exception(
        "django_utz couldn't import the zoneinfo module.\
         Perhaps you are on an older version of Python, run `pip install backports.zoneinfo` to continue."
        )

