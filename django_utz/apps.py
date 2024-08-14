from django.apps import AppConfig


class DjangoUtzConfig(AppConfig):
    name = "django_utz"

    def ready(self) -> None:
        import django_utz.signals
