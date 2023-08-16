# DJANGO USER TIMEZONE - django_utz

Django mixins to add timezone support to your models and serializers.

## Installation

Install with pip:

```bash
pip install django-utz
```

## Setup

Add `django_utz` to your `INSTALLED_APPS` setting:

```python
INSTALLED_APPS = [
    ...
    'django_utz',
]
```

To your User model, add the `UTZUserModelMixin` mixin:

```python
from django.contrib.auth.models import AbstractUser

from django_utz.models.mixins import UTZUserModelMixin

class User(UTZUserModelMixin, AbstractUser):
    '''User model'''
    pass
    
```

## Mixins

To use the mixins, simply subclass them in your model or serializer.

### The `UTZUserModelMixin` mixin

The `UTZUserModelMixin` mixin is meant to be used with the User model by sub classing the User model with it.

Here we will use [django-timezone-field]() to add timezone support to our User model. You can use any other timezone field you want.

```bash
pip install django-timezone-field
```

In settings.py:

```python

INSTALLED_APPS = [
    ...
    'django_utz',
    'timezone_field',
]
```

In models.py:

```python
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

from django_utz.models.mixins import UTZUserModelMixin
from timezone_field import TimeZoneField

class User(UTZUserModelMixin, AbstractBaseUser, PermissionsMixin):
    '''User model'''
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(max_length=255, unique=True)
    timezone = TimeZoneField(default="UTC")
    ...

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    user_timezone_field = "timezone" # valid user timezone info field name


user_1 = User.objects.create(
    username = "user_1",
    email = "userabc@gmail.com",
    timezone = "Africa/Lagos",
)
user_1.save()
print(user_1.timezone)
# Prints: Africa/Lagos
# Note this field returns a zoneinfo.ZoneInfo object or a pytz.timezone object depending on kwargs passed
```

In the code sample above, we can see that the `UTZUserModelMixin` mixin is used to add timezone support to the AbstractBaseUser model. The same can be done to the AbstractUser and default User model.

The `user_timezone_field` attribute is used to specify the field that contains the user timezone name. Say we create another User model with the `UTZUserModelMixin` mixin, but this time, we want to use another field called `tz_name` to store the user timezone name. We can do this by setting the `user_timezone_field` attribute to `tz_name`:

```python
import zoneinfo
from django.contrib.auth.models import AbstractUser

from django_utz.models.mixins import UTZUserModelMixin

class User(UTZUserModelMixin, AbstractUser):
    '''User model'''
    TIMEZONE_CHOICES = tuple((tz, tz) for tz in sorted(zoneinfo.available_timezones()))
    ...
    tz_name = models.CharField(max_length=255, blank=True, verbose_name="Timezone name", choices=TIMEZONE_CHOICES)
    ...
    user_timezone_field = "tz_name" # valid user timezone info field name


user_1 = User.objects.create(
    username = "user_1",
    email = "userabc@gmail.com",
    tz_name = "Africa/Lagos",
)
user_1.save()
print(user_1.tz_name)
# Prints: Africa/Lagos
# Note this field returns the timezone name as a string

```

However, to access the user's timezone info as a zoneinfo.ZoneInfo or pytz.timezone object anytime, we can use the `_utz_` property:

```python

user_1 = User.objects.get(pk=1)
print(type(user_1._utz_))
# Here, a zoneinfo.ZoneInfo object or pytz.timezone object is returned depending
```

#### Attributes

- `user_timezone_field`: The field that contains the user timezone name.
- `is_user_model`: This is a property used to determine if the model is the User model or not.
- `_utz_`: A property that returns the user timezone info as a zoneinfo.ZoneInfo or pytz.timezone object. This is used internally by the `to_local_timezone` method. If settings.USE_DEPRECATED_PYTZ is set to `True`, this property returns the user timezone info as a pytz.timezone object. If the `user_timezone_field` attribute is not set, this property returns a settings.TIME_ZONE or "UTC" zoneinfo.ZoneInfo or pytz.timezone object.

#### Methods

- `to_local_timezone`: Converts a datetime object to the user's local timezone.

    ```python
    from django.contrib.auth import get_user_model
    import timezone

    User = get_user_model()
    user = User.objects.get(pk=1)
    now = timezone.now()
    now_in_utz = user.to_local_timezone(now)
    print(f"The current time in {user.username}'s timezone is {now_in_utz:%Y-%m-%d %H:%M:%S %Z (%z)}")
    print(f"The current time in server's timezone is {now:%Y-%m-%d %H:%M:%S %Z (%z)}")
    ```

### The `UTZModelMixin` mixin

The `UTZModelMixin` mixin is meant to be used with any model (including the User model) by sub classing the model with it. This mixin automatically adds properties which return the timezone aware datetime fields of the model in the user's local timezone.

In my_app.models.py:

Let's say our User model is related to other models which have timezone aware datetime fields. We can add user timezone support to these models by sub classing them with the `UTZModelMixin` mixin so user timezone aware properties for the datetime fields are added to the models.

**NOTE: The model in which this mixin is used must be related to the User model which has been subclassed by the `UTZUserModelMixin`**

Let our timezone aware model be called `Post`:

```python
from django.db import models
from django.contrib.auth import get_user_model

from django_utz.models.mixins import UTZModelMixin

User = get_user_model()

class Post(UTZModelMixin, models.Model):
    '''Post model'''
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ...

    datetime_fields = ["created_at", "updated_at"]
    
```

Here our model `Post` is sub classed with the `UTZModelMixin` mixin. The `datetime_fields` attribute is used to specify the datetime fields in the model that we want to make user timezone aware properties for. In this case, the `created_at` and `updated_at` fields are the timezone aware datetime fields in the `Post` model that we need to create user timezone aware properties for. To access the user timezone aware datetime properties we use the fields name suffixed by "utz" (e.g. `created_at_utz` and `updated_at_utz`).

```python
from django.contrib.auth import get_user_model
from my_app.models import Post

User = get_user_model()

user_1 = User.objects.get(pk=1)
new_post = Post.objects.create(
    author = user_1,
    title = "New Post",
    content = "Lorem Ipsum",
)
new_post.save()
date_created_in_utz = new_post.created_at_utz
date_created_in_server_tz = new_post.created_at
print(date_created_in_utz: %Y-%m-%d %H:%M:%S %Z (%z))
print(date_created_in_server_tz: %Y-%m-%d %H:%M:%S %Z (%z))

```

To change the value with which the added properties are suffixed, we can set the `utz_property_suffix` attribute to a desired value:

```python
from django.db import models

from django_utz.models.mixins import UTZModelMixin

class Post(UTZModelMixin, models.Model):
    '''Post model'''
    ...
    datetime_fields = ["created_at", "updated_at"]
    utz_property_suffix = "local" # default is "utz"
    
```

Now we can access the user timezone aware datetime properties with the fields name suffixed by "local" (e.g. `created_at_local` and `updated_at_local`).

```python
from django.contrib.auth import get_user_model
from my_app.models import Post

User = get_user_model()
user_1 = User.objects.get(pk=1)
new_post = Post.objects.create(
    author = user_1,
    title = "New Post",
    content = "Lorem Ipsum",
)
new_post.save()
date_created_in_utz = new_post.created_at_local
date_created_in_server_tz = new_post.created_at
print(date_created_in_utz: %Y-%m-%d %H:%M:%S %Z (%z))
print(date_created_in_server_tz: %Y-%m-%d %H:%M:%S %Z (%z))

```

> This can also be used in the User model. That way user timezone aware datetime properties are added to the User model too.

#### Attributes

- `datetime_fields`: A list of the timezone aware datetime model fields that we want to create user timezone aware properties for. Defaults to an empty list.
- `utz_property_suffix`: The suffix with which the timezone aware (datetime/time) attributes are suffixed. Defaults to "utz".
- `is_user_model`: This is a property used to determine if the model is the User model or not.

#### Methods

- `find_user_related_model_field`: Returns the traversal path to the user related model field.

    ```python
    from django.contrib.auth import get_user_model
    from my_app.models import Post

    User = get_user_model()
    user_1 = User.objects.get(pk=1)
    new_post = Post.objects.create(
        author = user_1,
        title = "New Post",
        content = "Lorem Ipsum",
    )
    new_post.save()
    user_related_model_field = new_post.find_user_related_model_field()
    print(user_related_model_field)

    # result: author
    ```

### The `UTZModelSerializerMixin` mixin

The `UTZModelSerializerMixin` mixin is meant to be used with any django rest framework model serializer by sub classing the serializer with it. This mixin automatically adds user timezone aware serializer fields to the serializer for fields in the serializer's model that are present is the `datetime_fields` attribute.

**NOTE:**

1. The serializer's model must subclass the `UTZModelMixin` mixin.
2. If you need complete control over the serializer fields, you can set the `add_utz_fields` attribute to `False` or decide not to subclass the serializer with this mixin and add then the timezone aware serializer fields manually. Read more on timezone aware serializer fields [here](#serializer-fields).

Let's say we want to create a serializer for our model `Post`:

```python
from rest_framework import serializers
from django_utz.serializers.mixins import UTZModelSerializerMixin

from my_app.models import Post

class PostSerializer(UTZModelSerializerMixin, serializers.ModelSerializer):
    '''Post serializer'''
    class Meta:
        model = Post
        fields = "__all__"

# This way all fields in serializer.Meta.model.datetime_fields will be user timezone aware
```

You can use the `extra_kwargs` attribute to set keyword arguments for the automatically added fields:

```python
class PostSerializer(UTZModelSerializerMixin, serializers.ModelSerializer):
    '''Post serializer'''
    class Meta:
        model = Post
        fields = "__all__"
        extra_kwargs = {
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }
```

#### Attributes

- `add_utz_fields`: A boolean value that determines if the user timezone aware serializer fields should be automatically added to the serializer. Defaults to `True`.
- `datetime_repr_format`: The format with which the datetime fields are represented. Defaults to "%Y-%m-%d %H:%M:%S %Z (%z)".
- `serializer_model`: The model of the serializer. Returns serializer.Meta.model.

## Fields

### Serializer Fields

In the case that you need complete control over the serializer fields, you can add user timezone aware serializer datetime fields manually. The timezone aware serializer fields are:

- `UTZDateTimeField`: A serializer field that represents a timezone aware datetime field in the user's local timezone.

```python
class PostSerializer(serializers.ModelSerializer):
    '''Post serializer'''
    created_at = UTZDateTimeField(read_only=True, format="%Y-%m-%d %H:%M:%S %Z (%z)")
    updated_at = UTZDateTimeField(read_only=True, label="Last updated at", format="%Y-%m-%d %H:%M:%S %Z (%z)")
    class Meta:
        model = Post
        fields = "__all__"
```

## Signals

The `django_utz.models.signals` module contains signals that are sent when a user's timezone is updated. The signals are:

- `user_timezone_changed`: Sent when a user's timezone is updated.

In your receiver, you can access the user's old timezone and new timezone with the `old_timezone`, `new_timezone`, `user` keyword arguments and do whatever you want with them.

```python
from django.dispatch import receiver
from django_utz.models.signals import user_timezone_changed

@receiver(user_timezone_changed)
def user_timezone_changed_receiver(sender, **kwargs):
    old_timezone = kwargs.get("old_timezone")
    new_timezone = kwargs.get("new_timezone")
    print(old_timezone, new_timezone)
```

#### Contributors and feedbacks are welcome. For feedbacks, please open an issue or contact me at tioluwa.dev@gmail.com or on twitter [@ti_oluwa_](https://twitter.com/ti_oluwa_)

#### To contribute, please fork the repo and submit a pull request

#### If you find this module useful, please consider giving it a star. Thanks!
