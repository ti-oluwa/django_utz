"""
Module containing django rest framework serializers mixins and fields for the django_utz package.
"""
try:
    import rest_framework
except ImportError:
    raise Exception(
        "Using django_utz.serializers requires the installation of the django rest framework.\
         Perhaps you forgot to install it. Run `pip install djangorestframework` and\
         add 'rest_framework' to settings.INSTALLED_APPS to continue."
        )