"""
#### django_utz

Decorators for Django models and DRF model serializers, custom serializer fields,
template tags and filters that aid easy conversion of timezone aware fields to a user's timezone.
"""

__version__ = "0.3.1"
__author__ = "Daniel T. Afolayan"

alias = "django-user-timezone"

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo
except Exception:
    raise Exception(
        "django_utz couldn't import the zoneinfo module.\
         Perhaps you are on an older version of Python, run `pip install backports.zoneinfo` to continue."
    )
