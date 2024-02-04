"""
`django_utz` decorators for django rest framework model serializers and custom serializer fields.
"""
try:
    import rest_framework
except ImportError:
    raise Exception(
        "Using django_utz.decorators.serializers requires the installation of the django rest framework.\
         Perhaps you forgot to install it. Run `pip install djangorestframework` and\
         add 'rest_framework' to settings.INSTALLED_APPS to continue."
        )

from .decorators import ModelSerializerDecorator, modelserializer
