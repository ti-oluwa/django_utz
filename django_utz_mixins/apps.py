from django.apps import AppConfig


class DjangoUtzMixinsConfig(AppConfig):
    name = 'django_utz_mixins'

    def ready(self) -> None:
        import django_utz_mixins.signals
        return super().ready()