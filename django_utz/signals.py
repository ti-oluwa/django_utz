from django.contrib.auth import get_user_model
from django.dispatch import Signal
from django.db.models.signals import pre_save
from django.conf import settings


UserModel = get_user_model()

user_timezone_changed = Signal()
# ----------------------------------------------------
# This signal is sent when a user's timezone is changed.
# kwargs: instance, previous_timezone, current_timezone
# ----------------------------------------------------


def utz_change_handler(sender, **kwargs) -> None:
    """Signal handler for user timezone changes"""
    user = kwargs["instance"]
    utz_meta = getattr(sender, "UTZMeta", None)

    if utz_meta and utz_meta._decorated:
        tz_field = getattr(utz_meta, "timezone_field")
        try:
            previous_timezone = getattr(sender.objects.get(pk=user.pk), tz_field)
        except sender.DoesNotExist:
            previous_timezone = ""
        current_timezone = getattr(user, tz_field)

        if previous_timezone != current_timezone:
            user_timezone_changed.send(
                sender=sender,
                instance=user,
                previous_timezone=previous_timezone,
                current_timezone=current_timezone,
            )
    return None


# ----------------------------------------------------
# Connect the signal handler to the user model
# ----------------------------------------------------
if getattr(settings, "ENABLE_UTZ_SIGNALS", False) is True:
    pre_save.connect(utz_change_handler, sender=UserModel)
