from django.contrib.auth import get_user_model
from django.dispatch import Signal, receiver
from django.db.models.signals import pre_save

User = get_user_model()


user_timezone_changed = Signal(["user", "old_timezone", "new_timezone"])

@receiver(pre_save, sender=User)
def user_pre_save_handler(sender, **kwargs):
    """Sends signal when user timezone is changed before it is saved"""
    user = kwargs["instance"]
    tz_field = getattr(user, "user_timezone_field", None)
    old_timezone = getattr(User.objects.get(pk=user.pk), tz_field)
    new_timezone = getattr(user, tz_field)
    if old_timezone != new_timezone:
        user_timezone_changed.send(sender=User, user=user, old_timezone=old_timezone, new_timezone=new_timezone)
    return None