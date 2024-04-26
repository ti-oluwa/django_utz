# django-utz

django-utz provides easy-to-use decorators that allow you easily retrieve/display datetime values in the request user's or a specific user's local timezone without needing to do manual timezone conversions for each user.

"utz" here means "user time zone". This django app provides decorators for the project's User model, regular django models and django rest framework model serializers.

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

Add `django_utz.middleware.DjangoUTZMiddleware` to `MIDDLEWARE` just below `AuthenticationMiddleware`:

```python
MIDDLEWARE = [
    ...,
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_utz.middleware.DjangoUTZMiddleware',
]
```

You can then import and use the required user model decorator

```python
from django.contrib.auth.models import AbstractUser

from django_utz.decorators import usermodel


@usermodel
class CustomUser(AbstractUser):
    '''Project's user model'''
    email = models.EmailField()
    username = models.CharField(max_length=50)
    timezone = models.CharField(max_length=20)
    ...
    
    class UTZMeta:
        timezone_field = "timezone"
```

## Decorators

django_utz comes bundled with three decorators:

- `usermodel`: The project's User model must be decorated with this decorator for django_utz to work.
- `model`: Regular django models can be decorated with this decorator so that datetime fields in the model can be accessed in request.user's or any specified user local timezone always.
- `modelserializer`: Django rest framework model serializers can be decorated with this decorator so that the serializer's model datetime fields will always be returned in request.user's or any specified user local timezone in API responses.

Configurations for each model are defined in a `UTZMeta` class just inside the model or model serializer class.

For instance;

```python
from django.db import models

from django_utz.decorators import model

@model
class Post(models.Model):
    '''Post model'''
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ...
    
    class UTZMeta:
        datetime_fields = ["created_at", "updated_at"]
        use_related_user_timezone = True
        related_user = "author"
```

The possible configurations for each decorator will be discussed in the next sections.

### The `usermodel` decorator

The `usermodel` decorator is used to decorate the project's User model. This decorator basically adds django_utz support to the project. It adds a property to the User model that returns the user's timezone info as a zoneinfo.ZoneInfo or pytz.tzinfo object. It also adds a method to the User model that converts a datetime object to the user's local timezone and returns a `utzdatetime` object.

Let's look at an example of how you would use the `usermodel` decorator:

Here we will use [django-timezone-field](https://github.com/mfogel/django-timezone-field/) to add a timezone field to our User model. You can use any field you want.

```bash
pip install django-timezone-field
```

In settings.py, add `timezone_field` to `INSTALLED_APPS`:

```python

INSTALLED_APPS = [
    ...,
    'django_utz',
    'timezone_field',
]
```

In models.py, let's create a User model and decorate it with the `usermodel` decorator:

```python
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

from django_utz.decorators import usermodel
from timezone_field import TimeZoneField

@usermodel
class CustomUser(AbstractBaseUser, PermissionsMixin):
    '''User model'''
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(max_length=255, unique=True)
    timezone = TimeZoneField(default="UTC")
    ...

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "Custom user"
        verbose_name_plural = "Custom users"

    class UTZMeta:
        timezone_field = "timezone" # valid user timezone info field name
```

Simple right! Now let's look at the configurations for the `usermodel` decorator.

The only configuration for the `usermodel` decorator is the `timezone_field` attribute. This attribute is used to specify the field that contains the user timezone info or name, as seen in the example above.

The `usermodel` decorator adds a property and a method to the User model. It can be said these added property and method are the backbone of the `django_utz` module. Let's look at them:

- The `utz` property: This property returns the user's timezone info as a zoneinfo.ZoneInfo or pytz.tzinfo object, even if the user's timezone is stored as a string in the database. 

The type of timezone info object returned depends mainly on the `USE_DEPRECATED_PYTZ` setting. If `USE_DEPRECATED_PYTZ` is set to `True`, the timezone info object returned will be a pytz.tzinfo object. Otherwise, the timezone info object returned will be a zoneinfo.ZoneInfo object.

- The `to_local_timezone` method: This method converts any datetime object passed to it to a `utzdatetime` object in the user's local timezone as returned by the `utz` property.

To see how these work, we can create a user instance and use the `utz` property and `to_local_timezone` method:

```python
from django.utils import timezone

my_user = CustomUser.objects.create_user(
    username="Tolu",
    email="testing321@gmail.com",
    password="testing321",
    timezone="Africa/Lagos"
)

# Getting the user's timezone info
user_timezone = my_user.utz
print(user_timezone) # Africa/Lagos
print(type(user_timezone)) # zoneinfo.ZoneInfo, assuming USE_DEPRECATED_PYTZ is set to False

# Converting a datetime object in server's timezone (UTC) to user's local timezone
now = timezone.now()
print(now) # 1996-12-19 16:39:57.000200+00:00
now_in_user_tz = my_user.to_local_timezone(now)
print(now_in_user_tz) # 1996-12-19 17:39:57.000200+01:00
```

In the above example, we can see that the current time in the user's timezone is one hour ahead of the current time in the server's timezone.

> Note that the `to_local_timezone` method returns a `utzdatetime` object. This is because the `utzdatetime` object is independent of settings.USE_TZ. This means that the `utzdatetime` object will always be in the user's timezone regardless of the value of settings.USE_TZ. Read more on the `utzdatetime` object [here](#the-utzdatetime-object).

### The `model` decorator

The `model` decorator is used to decorate regular django models. This decorator allows you to access model datetime fields in a user's local timezone. The user can be the request user or any specified user. By default, the request user is used.

Curious about how this works? To keep things simple, the decorator uses a kind of descriptor called the `FunctionAttribute` descriptor to add a new version of each datetime field to the model class. This new version of the datetime field is suffixed with "utz"(by default) and is a property that returns the datetime field in the user's local timezone.

Say for example, we have a model called `Post` and we want to access the `created_at` field in the request user's timezone.

```python
from django.db import models

from django_utz.decorators import model

@model
class Post(models.Model):
    '''Post model'''
    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ...

    class UTZMeta:
        datetime_fields = "__all__"
```

The decorator adds a new attribute to the `Post` model called `created_at_utz`. Let's create a post instance and see how this works:

```python
from django.contrib.auth import get_user_model

User = get_user_model()

tolu = User.objects.get(username="Tolu")

new_post = Post.objects.create(
    title="New Post",
    content="Lorem Ipsum",
    author=tolu
)

# If the post was created at 12:00:00 UTC, it will be 13:00:00 in the user's timezone.
# Remember, Tolu's timezone is "Africa/Lagos"
print(new_post.created_at_utz) # 1996-12-19 13:00:00.000200+01:00
```

The `model` decorator has a few configurations one of which was used in the model definition above. The configurations are:

- `datetime_fields`: A list or tuple of the model's datetime fields for which user timezone aware fields should be added. If set to `"__all__"`, all datetime fields in the model will have user timezone aware fields added.

- `use_related_user_timezone`: An optional boolean value that determines if the user timezone aware fields should be based on the timezone of a directly related user, not the request user. This defaults to `False`.

The related user in the case of the `Post` model is the `post.author`. If a related user is not found directly in the model, django_utz tries to search for a user in the related models of the model. A related model is usually a model that is linked by a ForeignKey or OneToOneField to the current model.

To define explicitly the user whose timezone will be used, you can set this comfiguration to `True` and then defined the path to user on the `related_user` configuration.

- `related_user`: This is also an optional configuration that specifies the path to the user whose timezone will be used. This is only used when `use_related_user_timezone` is set to `True`. The path is a string that represents the path to the user from the model. The path is in the format `related_model.related_model....user_field`. 

Looks complicated? Let's look at two examples:

**Example 1:**

Assume we want all datetime fields in the `Post` model to always be returned in the post author's timezone. We can do this:

```python
from django.db import models

from django_utz.decorators import model

@model
class Post(models.Model):
    '''Post model'''
    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ...

    class UTZMeta:
        datetime_fields = "__all__"
        use_related_user_timezone = True
        related_user = "author"
```

So no matter the user that makes the request, the datetime fields in the `Post` model will always be returned in the post author's timezone.

You could also decide to not specify the `related_user` configuration. django_utz will use the first user it finds in the related models of the model. Which is the `author` in this case.

**Example 2:**

Let's add a new model called `Comment` that is related to the `Post` model. However, we want all datetime fields in the `Comment` model to always be returned in the post author's timezone. We can do this:

```python
from django.db import models

from django_utz.decorators import model

@model
class Comment(models.Model):
    '''Comment model'''
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ...

    class UTZMeta:
        datetime_fields = "__all__"
        use_related_user_timezone = True
        related_user = "post.author"
```

In this case, the `related_user` configuration is set to `"post.author"`. This means that the datetime fields in the `Comment` model will always be returned in the post author's timezone, not the comment author's timezone (to be clear, the comment author is the user that made the comment).

Hence, Assuming 'Tolu' already created a new post called 'new_post' and we created a user called 'Tade' with a timezone of "Asia/Tokyo", we can do this:

```python
tade = User.objects.get(username="Tade")

comment = Comment.objects.create(
    post=new_post,
    author=tade,
    content="Nice post!"
)

print(comment.created_at_utz) # 1996-12-19 13:00:00.000200+01:00 (Africa/Lagos)
print(comment.author.utz) # Asia/Tokyo
print(comment.author.to_local_timezone(comment.created_at)) # 1996-12-19 21:00:00.000200+09:00 (Asia/Tokyo)
```

- `attribute_suffix`: This is an optional configuration that specifies the suffix to be added to the user timezone aware fields. This defaults to "utz".

You may want to access created_at in the user's timezone as `created_at_local` instead of `created_at_utz`. You can do this:

```python

@model
class Post(models.Model):
    '''Post model'''
    ...

    class UTZMeta:
        ...
        attribute_suffix = "local"
```

### The `modelserializer` decorator

This decorator is used to decorate django rest framework model serializers. As said at the beginning, this decorator allows you to always return the serializer's model datetime fields in the request user's local timezone or any specified user's local timezone(based on the configurations in the serializer's model) in API responses.

However, for the decorator to work, the serializer's model must have also been decorated with the `model` decorator.

Let's say we want to create a serializer for our model `Post`:

```python
from rest_framework import serializers
from django_utz.decorators import modelserializer

from my_app.models import Post

@modelserializer
class PostSerializer(serializers.ModelSerializer):
    '''Post serializer'''
    class Meta:
        model = Post
        fields = "__all__"

    class UTZMeta:
        auto_add_fields = True

```

The available configurations for the `modelserializer` decorator are:

- `auto_add_fields`: This is a boolean value that determines if the decorator should automatically add timezone aware serializer fields to the serializer. This defaults to `True`.

- `datetime_format`: This is an optional string that specifies the format to be used when serializing the datetime fields.

> If you need complete control over the serializer fields, you can set the `auto_add_fields` config to `False` or decide not to decorate the model serializer and then add the timezone aware serializer fields manually. Read more on timezone aware serializer fields [here](#serializer-fields).

Also, you do not need to worry about the serializers Meta configuration not been applied. The `modelserializer` decorator respects the Meta configuration of the serializer so all excluded fields, read_only fields, and extra keyword arguments etc will be respected.

## Fields

### Serializer Fields

In the case that you need complete control over the auto-added serializer fields, you can add user timezone aware serializer datetime fields manually.

- `UTZDateTimeField`: A serializer field that represents a timezone aware datetime field in the preferred user's local timezone (as defined in the serializer's model).

```python
from rest_framework import serializers

from django_utz.serializers_fields import UTZDateTimeField

class PostSerializer(serializers.ModelSerializer):
    '''Post serializer'''
    created_at = UTZDateTimeField(read_only=True, format="%Y-%m-%d %H:%M:%S %Z (%z)")
    updated_at = UTZDateTimeField(read_only=True, label="Last updated at", format="%Y-%m-%d %H:%M:%S %Z (%z)")

    class Meta:
        model = Post
        fields = "__all__"
```

## Signals

The `django_utz.signals` module contain signals that are sent when an event occurs on a user's timezone. The signals are:

- `user_timezone_changed`: Sent when a user's timezone is updated.

> These signals are disabled by default. To ensure that the signals are sent set `ENABLE_UTZ_SIGNALS` to `True` in your settings.py file.

In your receiver, you can access the user object, its previous timezone and current timezone with the `instance`, `previous_timezone`and `current_timezone` keyword arguments respectively.

```python
from django.dispatch import receiver
from django_utz.signals import user_timezone_changed

@receiver(user_timezone_changed)
def timezone_change_handler(sender, **kwargs):
    old_timezone = kwargs.get("previous_timezone")
    new_timezone = kwargs.get("current_timezone")
    print(old_timezone, new_timezone)
```

## Templates

### Template Tags

The `django_utz.templatetags.django_utz` module contains a template tag that allows you to display datetime objects in the preferred user's local timezone. To use in a template, load the module in your template:

```html
{% load django_utz %}
```

- `usertimezone`: This is a block tag that renders template content with datetime object(s) contained within the block in the request user's timezone but the preferred user can be passed as an argument or keyword argument. Assuming that we want to write a template for our post list view, we can do this:

Here the datetime objects, `post.created_at` is rendered in the request user's timezone:

```html
{% load django_utz %}
{% usertimezone %}
    {% for post in posts %}
        <h3>{{ post.title }}</h3>
        <p>{{ post.created_at }}</p>
        <p>{{ post.author }}</p>
    {% endfor %}
{% endusertimezone %}
```

Say we want to render the datetime object, `post.created_at` in the timezone of the author of the first post, we can do this:

First approach:

```html
{% load django_utz %}
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
{% load django_utz %}
{% usertimezone user=posts[0].author %}
    {% for post in posts %}
        <h3>{{ post.title }}</h3>
        <p>{{ post.created_at }}</p>
        <p>{{ post.author }}</p>
    {% endfor %}
{% endusertimezone %}
```

### Template Filters

django_utz also provides a template filter that allows you to display datetime objects in the preferred user's local timezone.

- `usertimezone`: This filter returns a datetime object in the request user's timezone but the preferred user can be passed as an argument.

Say we want to write a template for our post detail view, we can do this:

```html
{% load django_utz %}

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

## The `utzdatetime` object

This is a custom datetime that can be independent of settings.USE_TZ. It inherits from `datetime.datetime`. The reason this exists is because when USE_TZ is set to True, sometimes, datetime objects are converted back to the server's timezone. This can be a problem when you want to view datetime objects in a timezone other than the server's timezone.

A peculiar case is in templates. If you try to access say, `post.created_at_utz` in a template, you'd get the datetime object in the server's timezone. This is because the datetime object is converted back to the server's timezone when USE_TZ is set to True. Hence, the reason why a `utzdatetime` is used.

This object is timezone aware and can be used to display datetime objects in any timezone.

> This concept was gotten from `django.templatetags.tz`'s `datetimeobject`.

The `utzdatetime` object has the following methods:

- `from_datetime(cls, _datetime: datetime.datetime)`: This class method allows the construction of a `utzdatetime` object from a datetime object.

```python
import datetime
from django_utz.datetime import utzdatetime

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

**Contributions and feedbacks are welcome. For feedbacks, please open an issue. To contribute, please fork the repo and submit a pull request. Thanks!**
