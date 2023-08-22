"""django_utz template tags and filters"""
from typing import Dict, List
from django.template.base import Parser, Token, Node, FilterExpression, kwarg_re
from django.template import Library, TemplateSyntaxError, NodeList
from django.conf import settings
from django.utils import timezone
import datetime

from django_utz.models.mixins import UTZUserModelMixin
from django_utz.middleware import get_request_user


register = Library()
_generic_name = "usertimezone"

def parse_tag(token: Token, parser: Parser):
    """
    Generic template tag parser.

    Returns a three-tuple: (tag_name, args, kwargs)

    tag_name is a string, the name of the tag.

    args is a list of FilterExpressions, from all the arguments that didn't look like kwargs,
    in the order they occurred, including any that were mingled amongst kwargs.

    kwargs is a dictionary mapping kwarg names to FilterExpressions, for all the arguments that
    looked like kwargs, including any that were mingled amongst args.

    (At rendering time, a FilterExpression f can be evaluated by calling f.resolve(context).)
    """
    bits = token.split_contents()
    tag_name = bits.pop(0)

    # Parse the rest of the args, and build FilterExpressions from them so that
    # we can evaluate them later.
    args = []
    kwargs = {}
    for bit in bits:
        # Is this a kwarg or an arg?
        match = kwarg_re.match(bit)
        kwarg_format = match and match.group(1)
        if kwarg_format:
            key, value = match.groups()
            kwargs[key] = FilterExpression(value, parser)
        else:
            args.append(FilterExpression(bit, parser))
    return tag_name, args, kwargs


class UTZNode(Node):
    """Node to render the template content in the user's timezone"""
    def __init__(
            self, nodelist: NodeList, 
            args: List[FilterExpression], 
            kwargs: Dict[str, FilterExpression], 
            tag_name: str
        ):
        self.nodelist = nodelist
        self.user = self.get_user(args, kwargs, tag_name)
        self.tag_name = tag_name


    @staticmethod
    def get_user(
        args: List[FilterExpression], 
        kwargs: Dict[str, FilterExpression], 
        tag_name: str
        ):
        """
        Get the user object from the arguments and keyword arguments passed to the template tag.
        """
        if args:
            if len(args) != 1:
                raise TemplateSyntaxError(
                    f"{tag_name} requires exactly one argument. The user object\
                    whose timezone is to be used to render the template content."
                )
            user = args[0]
        else:
            user = kwargs.get("user", None)
        return user


    def render(self, context):
        user = context.get("request").user
        if self.user:
            preferred_user = self.user.resolve(context)
        user = preferred_user if preferred_user else user

        if user.is_authenticated and issubclass(user.__class__, UTZUserModelMixin):
            tz = user.utz
        else:
            tz = settings.TIME_ZONE if settings.USE_TZ else "UTC"

        original_timezone = timezone.get_current_timezone()
        try:
            timezone.activate(tz)
            output = self.nodelist.render(context)
        finally:
            timezone.activate(original_timezone)
        return output


@register.tag(name=_generic_name)
def utz_tag(parser: Parser, token: Token):
    """
    Template tag to render the template content in the preferred user's timezone.

    #### In your template:
    To render the template content in the timezone of the user object passed as an argument:
    ```
    {% load utz %}
    {% usertimezone user=object.user %}
        {# Your template content #}
    {% endusertimezone %}
    ```

    To render the template content in the timezone of the request user:
    ```
    {% load utz %}
    {% usertimezone %}
        {# Your template content #}
    {% endusertimezone %}
    ```
    """
    tag_name, args, kwargs = parse_tag(token, parser)
    nodelist = parser.parse((f"end{_generic_name}",))
    parser.delete_first_token()
    return UTZNode(nodelist, args, kwargs, tag_name)


@register.filter(name=_generic_name)
def utz_filter(value: datetime.datetime, user: UTZUserModelMixin = None):
    """
    Filter to convert a datetime object to the user's timezone.

    If the user is not authenticated or the user model is not a subclass of UTZUserModelMixin,
    the value is returned as is.

    An optional user object can be passed as an argument to the filter.

    #### In your template:
    ```
    {% load utz %}
    {{ datetime_object|usertimezone }}
    ```
    A specific user whose timezone would be used can also be provided:
    ```
    {% load utz %}
    {{ datetime_object|usertimezone:user }}
    ```
    """
    if not user: # If no user is provided, use the request user
        user = get_request_user()
    # If the user model is not a subclass of UTZUserModelMixin, return the value as is
    if not issubclass(user.__class__, UTZUserModelMixin):
        return value
    try:
        return user.to_local_timezone(value)
    except Exception:
        return value
    
