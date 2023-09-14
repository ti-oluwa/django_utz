"""
#### django_utz

This package contains mixins and utils for Django models, DRF model serializers and fields, 
template tags and filters that aid easy conversion of timezone aware fields to the user's timezone.

@Author: Daniel T. Afolayan (ti-oluwa.github.io)
"""

__version__ = "0.1.5"
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
