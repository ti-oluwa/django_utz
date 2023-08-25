# django-utz

Django mixins that allow you retrieve datetime model fields in the preferred user's local timezone. "utz" here means "user timezone". This modules provides mixins for the User model, any other model and any django rest framework model serializer.

## Installation

Install with pip:

```bash
pip install django-utz
```

## Setup

Add `django_utz` to your `INSTALLED_APPS` setting:

```python
INSTALLED_APPS = [
    ...,
    'django_utz',
]
```

Add `django_utz.middleware.DjangoUTZMiddleware` to `MIDDLEWARE`

```python
MIDDLEWARE = [
    ...,
    'django_utz.middleware.DjangoUTZMiddleware',
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

#### Attributes

- `user_timezone_field`: The field that contains the user timezone info.
- `utz`: A property that returns the user timezone info as a zoneinfo.ZoneInfo or pytz.timezone object. This is used internally by the `to_local_timezone` method. If settings.USE_DEPRECATED_PYTZ is set to `True`, this property returns the user timezone info as a pytz.timezone object. If the `user_timezone_field` attribute is not set, this property returns a settings.TIME_ZONE or "UTC" zoneinfo.ZoneInfo or pytz.timezone object.

Here we will use [django-timezone-field](https://github.com/mfogel/django-timezone-field/) to add timezone support to our User model. You can use any other timezone field you want.

```bash
pip install django-timezone-field
```

In settings.py:

```python

INSTALLED_APPS = [
    ...,
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
# Note this field returns a zoneinfo.ZoneInfo object or a pytz.tzinfo object depending on keyword arguments passed to the field
```

In the code sample above, we can see that the `UTZUserModelMixin` mixin was added to our AbstractBaseUser model. The same can be done to the AbstractUser and default User model.

The `user_timezone_field` attribute is used to specify the field that contains the user timezone info or name. Say we create another User model with the `UTZUserModelMixin` mixin, but this time, we want to use another field called `tz_name` to store the user timezone name. We can do this by setting the `user_timezone_field` attribute to `tz_name`:

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

However, to access the user's timezone info as a zoneinfo.ZoneInfo or pytz.timezone object anytime, we can use the `utz` property:

```python

user_1 = User.objects.get(pk=1)
print(type(user_1.utz))
# Here, a zoneinfo.ZoneInfo object or pytz.timezone object is returned depending
```

#### Methods

- `to_local_timezone(_datetime: datetime.datetime)`: Converts a datetime object to the user's local timezone and returns a
`utzdatetime` object.

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

- `is_user_model()`: This is a class method that returns `True` if the model in which this mixin is used is the User model and `False` otherwise.

### The `UTZModelMixin` mixin

The `UTZModelMixin` mixin can be used in any model including the User model, by sub classing the model with it. This mixin automatically adds properties which return the values datetime model fields of the model in the preferred user's local timezone.

#### Attributes

- `datetime_fields`: A list of the datetime model fields that we want preferred user timezone aware properties for. Defaults to an empty list. Should be overridden in the model that subclasses this mixin.
- `utz_property_suffix`: The string with which the user timezone aware datetime properties are suffixed. Defaults to "utz".
- `use_related_user_timezone`: If True, the mixin gets the user related to the model(as specified or automatically) and uses its timezone. If False, the mixin uses the request user's timezone. Defaults to False.
- `related_user_field_path`: The name/traversal path of the field in the model in which this mixin is used, that holds/returns the preferred user.

> **NOTE: "Preferred user" as used in context here refers to the user who timezone zone will be used and by default, refers to the authenticated `request.user`. However, if `use_related_user_timezone` is set to True, the preferred user to be used can also be specified by providing the traversal path user field, to the `related_user_field_path` attribute but if left empty, the mixin will try to find the traversal path to the related user itself. In the case that the mixin has to search for the related user itself, the traversal path to the field holding the preferred user will be the traversal path of the "FIRST" One-to-One or ForeignKey field associated with the user model. Also note that all request users will now be fed the timezone adjusted datetime fields in that one single timezone as it will no longer be unique for each `request.user`. Check the last example in this section for more info on implementation.**

In my_app.models.py:

Let's say our User model is related to other models which have timezone aware datetime fields. We can add user timezone support to these models by sub classing them with the `UTZModelMixin` mixin so user timezone aware properties for the datetime fields are added to the models.

Let's create a model called `Post` in "my_app" app:

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

Here our model `Post` is sub classed with the `UTZModelMixin` mixin. The `datetime_fields` attribute is used to specify the datetime fields in the model that the new properties will be added for. In this case, the `created_at` and `updated_at` fields are the datetime fields in the `Post` model that we need in the preferred user's timezone. To access the user timezone aware datetime properties we use the fields name suffixed by "utz" (e.g. `created_at_utz` and `updated_at_utz`).

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
print(date_created_in_utz: %Y-%m-%d %H:%M:%S %Z (%z)) # In request user's timezone
print(date_created_in_server_tz: %Y-%m-%d %H:%M:%S %Z (%z)) # In server's timezone

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
print(date_created_in_utz: %Y-%m-%d %H:%M:%S %Z (%z)) # In request user's timezone
print(date_created_in_server_tz: %Y-%m-%d %H:%M:%S %Z (%z)) # In server's timezone

```

> This mixin can also be used in the User model alongside the `UTZUserModelMixin` mixin.

To display the datetime fields in the post.author's timezone for all users, we can set the `use_related_user_timezone` attribute to `True` and optionally set `related_user_field_path` as well:

```python
from django.db import models

from django_utz.models.mixins import UTZModelMixin

class Post(UTZModelMixin, models.Model):
    '''Post model'''
    ...
    datetime_fields = ["created_at", "updated_at"]
    use_related_user_timezone = True
    related_user_field_path = "author" # This can also be a traversal path to the field holding the preferred user, e.g "author.user"

# Now all users, regardless of their individual timezones, will see the datetime fields in the post.author's timezone
post = Post.objects.get(pk=1)
print(post.created_at_utz)
```

You may want to use this configuration only if you want all users to see the datetime fields in the same timezone (that is, the timezone of the user related to that object). This is useful for applications that are not user specific. 

An example use case would be in a foreign TV show app that shows the time a show will be live/viewable in the timezone of the country where the show is streamed from for all users. This is not a perfect example but I hope you get the idea.

#### Methods

- `find_user_related_model_field()`: Returns the traversal path to the field related to the User model in the model in which
    this mixin is used or its related models.

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

- `get_preferred_user()`: Returns the preferred user to be used. If `use_related_user_timezone` is set to `True`, the user related to the model will be returned(as specified or otherwise). If `use_related_user_timezone` is set to `False`, the request user will be returned. Read the docstring for more info.

- `is_user_model()`: This is a class method that returns `True` if the model in which this mixin is used is the User model and `False` otherwise.

### The `UTZModelSerializerMixin` mixin

The `UTZModelSerializerMixin` mixin is meant to be used with any django rest framework model serializer by sub classing the serializer with it. This mixin automatically adds preferred user timezone aware serializer fields to the serializer for fields in the serializer's model that are present in the serializer model's `datetime_fields` attribute.

#### Attributes

- `add_utz_fields`: A boolean value that determines if the user timezone aware serializer datetime fields should be automatically added to the serializer. Defaults to `True`.
- `datetime_repr_format`: The format with which the datetime fields are represented. Defaults to "%Y-%m-%d %H:%M:%S %Z (%z)".
- `serializer_model`: The model of the serializer. Returns serializer.Meta.model.

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

## Fields

### Serializer Fields

In the case that you need complete control over the serializer fields, you can add user timezone aware serializer datetime fields manually.

- `UTZDateTimeField`: A serializer field that represents a timezone aware datetime field in the preferred user's local timezone.

```python
from rest_framework import serializers

from django_utz.serializers.fields import UTZDateTimeField

class PostSerializer(serializers.ModelSerializer):
    '''Post serializer'''
    created_at = UTZDateTimeField(read_only=True, format="%Y-%m-%d %H:%M:%S %Z (%z)")
    updated_at = UTZDateTimeField(read_only=True, label="Last updated at", format="%Y-%m-%d %H:%M:%S %Z (%z)")
    class Meta:
        model = Post
        fields = "__all__"
```

## Signals

The `django_utz.models.signals` module contains signals that are sent when an event occurs on a user's timezone. The signals are:

- `user_timezone_changed`: Sent when a user's timezone is updated.

In your receiver, you can access the user object, its previous timezone and current timezone with the `user`, `previous_timezone`and `current_timezone` keyword arguments respectively.

```python
from django.dispatch import receiver
from django_utz.models.signals import user_timezone_changed

@receiver(user_timezone_changed)
def user_timezone_changed_receiver(sender, **kwargs):
    old_timezone = kwargs.get("previous_timezone")
    new_timezone = kwargs.get("current_timezone")
    print(old_timezone, new_timezone)
```

## Templates

### Template Tags

The `django_utz.templatetags.utz` module contains template tags that allow you to display datetime objects in the preferred user's local timezone. To use in a template, load the module in your template:

```html
{% load utz %}
```

Available template tags include:

- `usertimezone`: This is a block tag that renders template content with datetime object(s) contained within the block in the request user's timezone but the preferred user can be passed as an argument or keyword argument. Assuming that we want to write a template for our post list view, we can do this:

Here the datetime objects, `post.created_at` is rendered in the request user's timezone:

```html
{% load utz %}
{% usertimezone %}
    {% for post in posts %}
        <h3>{{ post.title }}</h3>
        <p>{{ post.created_at }}</p>
        <p>{{ post.author }}</p>
    {% endfor %}
{% endusertimezone %}
```

Say we want to render the datetime objects, `post.created_at` in the timezone of the author of the first post, we can do this:

First approach:

```html
{% load utz %}
{% usertimezone posts[0].author %}
    {% for post in posts %}
        <h3>{{ post.title }}</h3>
        <p>{{ post.created_at }}</p>
        <p>{{ post.author }}</p>
    {% endfor %}
{% endusertimezone %}
```

Alternatively;

```html
{% load utz %}
{% usertimezone user=posts[0].author %}
    {% for post in posts %}
        <h3>{{ post.title }}</h3>
        <p>{{ post.created_at }}</p>
        <p>{{ post.author }}</p>
    {% endfor %}
{% endusertimezone %}
```

### Template Filters

There are also template filters that allow you to display datetime objects in the preferred user's local timezone. Available template filters include:

- `usertimezone`: This filter returns a datetime object in the request user's timezone but the preferred user can be passed as an argument or keyword arguments.
Assuming that we want to write a template for our post detail view, we can do this:

```html
{% load utz %}

<h3>{{ post.title }}</h3>
<p>{{ post.content }}</p>
<p>{{ post.created_at|usertimezone }}</p>
<p>{{ post.author }}</p>
```

This works the same way as the `usertimezone` template tag.
We can also pass the preferred user as an argument:

```html
{% load utz %}

<h3>{{ post.title }}</h3>
<p>{{ post.content }}</p>
<p>{{ post.created_at|usertimezone:post.author }}</p>
<p>{{ post.author }}</p>
```

## Utilities

### The `django_utz.utils` module

The `django_utz.utils` module contains utility functions that can be used when handling timezone/datetime related activities.
Some of these functions include:

- `validate_timezone(value)`: This is a validator function that validates a timezone name or timezone info object. It raises a ValidationError if the value is not a valid timezone name or timezone info object.

Simple usage:

```python
from django_utz.utils import validate_timezone

validate_timezone("Africa/Lagos")
# No error raised
# Returns "Africa/Lagos"

validate_timezone("Africa/Lagos1")
# ValidationError raised
```

This is intended to be used as a model or serializer field validator.

- `is_timezone_vaild(timezone: str | datetime.tzinfo)`: This is a function that checks if a timezone name or timezone info object is valid. It returns `True` if the timezone is valid and `False` otherwise.

Sample usage:

```python
from django_utz.utils import is_timezone_valid

is_timezone_valid("Africa/Lagos")
# Returns True

is_timezone_valid("Africa/Lagos1")
# Returns False
```

- `get_attr_by_traversal(obj: object, traversal_path: str, default=None)`: This is a function that returns the value of an attribute of an object by traversing the object's attributes using the traversal path. It returns the value of the attribute if found and `default` otherwise.

Sample usage:

```python
from django_utz.utils import get_attr_by_traversal

class A:
    def __init__(self, b):
        self.b = b

class B:
    def __init__(self, c):
        self.c = c

class C:
    def __init__(self, d):
        self.d = d

obj = A(B(C("Hello World")))
print(get_attr_by_traversal(obj, "b.c.d"))
# Prints: Hello World
```

- `is_datetime_field(model: models.Model, field_name: str)`: This is a function that checks if a field in a model is a datetime field. It returns `True` if the field is a datetime field and `False` otherwise.

Sample usage:

```python
from my_app.models import Post
from django_utz.utils import is_datetime_field

is_datetime_field(Post, "created_at")
# Returns True

is_datetime_field(Post, "title")
# Returns False
```

- `is_time_field(model: models.Model, field_name: str)`: This is a function that checks if a field in a model is a time field. It returns `True` if the field is a time field and `False` otherwise.

Sample usage:

```python
from my_app.models import Post
from django_utz.utils import is_time_field

is_time_field(Post, "created_at")
# Returns False
```

- `is_date_field(model: models.Model, field_name: str)`: This is a function that checks if a field in a model is a date field. It returns `True` if the field is a date field and `False` otherwise.

Sample usage:

```python
from my_app.models import Post
from django_utz.utils import is_date_field

is_date_field(Post, "created_at")
# Returns False
```

### The `utzdatetime` object

This is a custom datetime that can be independent of settings.USE_TZ. It inherits from `datetime.datetime`. The reason this exists is because when USE_TZ is set to True, sometimes, datetime objects are converted back to the server's timezone. This can be a problem when you want to view datetime objects in a timezone other than the server's timezone.

A peculiar case is in templates. If you try to access say, `post.created_at_utz` in a template, you'd get the datetime object in the server's timezone. This is because the datetime object is converted back to the server's timezone when USE_TZ is set to True. Hence, a `utzdatetime` is returned by the `to_local_timezone` method of the `UTZUserModelMixin` mixin.

This object is timezone aware and can be used to display datetime objects in any timezone.

> This concept was gotten from `django.templatetags.tz`'s `datetimeobject`.

#### Custom Methods

- `from_datetime(cls, _datetime: datetime.datetime)`: This class method allows the construction of a `utzdatetime` object from a datetime object.

```python
import datetime
from django_utz.utils import utzdatetime

normal_datetime = datetime.datetime.now()
utz_datetime = utzdatetime.from_datetime(normal_datetime)
```

- `regard_usetz()`: This method makes the `utzdatetime` object respect settings.USE_TZ when being converted to a timezone. It may be converted back to server's timezone if USE_TZ is set to True.

```python
utz_datetime.regard_usetz()
# Now the utzdatetime object is dependent on settings.USE_TZ
```

- `disregard_usetz()`: This method makes the `utzdatetime` object disregard settings.USE_TZ when being converted to a timezone. It will not be converted back to server's timezone if USE_TZ is set to True.

```python
utz_datetime.disregard_usetz()
# Now the utzdatetime object is independent of settings.USE_TZ
```

**Contributors and feedbacks are welcome. For feedbacks, please open an issue. To contribute, please fork the repo and submit a pull request. If you find this module useful, please consider giving it a star. Thanks!**
