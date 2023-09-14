from django.contrib.auth import get_user_model
from django.dispatch import Signal, receiver
from django.db.models.signals import pre_save, post_save

from django_utz.models.mixins import UTZUserModelMixin

User = get_user_model()
# -----------------------------
user_timezone_changed = Signal()
# This signal is sent when a user's timezone is changed.
# kwargs: user, previous_timezone, current_timezone
# -----------------------------

@receiver(pre_save, sender=User)
def utz_change_handler_pre_save(sender, **kwargs):
    """High level signal handler for user timezone changes"""
    user = kwargs["instance"]
    if issubclass(user.__class__, UTZUserModelMixin):
        tz_field = getattr(user, "user_timezone_field")
        try:
            previous_timezone = getattr(User.objects.get(pk=user.pk), tz_field)
        except User.DoesNotExist:
            previous_timezone = ''
        current_timezone = getattr(user, tz_field)

        @receiver(post_save, sender=sender)
        def utz_change_handler_post_save(sender, **kwargs):
            """Sends signal when user timezone is changed after it is saved"""
            created = kwargs["created"]
            if not created and previous_timezone != current_timezone:
                user_timezone_changed.send(
                    sender=sender, 
                    user=user, 
                    previous_timezone=previous_timezone, 
                    current_timezone=current_timezone
                )
            return None
    return None
