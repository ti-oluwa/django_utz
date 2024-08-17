"""`django_utz` template tags and filters"""

from typing import Dict, List, Optional
import datetime
from django.template.base import Parser, Token, Node, FilterExpression, kwarg_re
from django.template import Library, TemplateSyntaxError, NodeList
from django.utils import timezone
from django.utils.safestring import SafeText

from ..middleware import get_request_user
from ..decorators.models import UserModelUTZMixin
from ..datetime import utzdatetime
from ..decorators.models import get_user_model_config

register = Library()
_generic_name = "usertimezone"


def parse_tag(token: Token, parser: Parser):
    """
    Generic template tag parser.

    Returns a three-tuple: (tag_name, args, kwargs)

    tag_name is a string, the name of the tag.

    args is a list of FilterExpressions, from all the arguments that didn't look like kwargs,
    in the order they occurred, including any that were amongst kwargs.

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
    """
    Node to render the datetimes in template content
    in the preferred user's timezone.
    """

    def __init__(
        self,
        nodelist: NodeList,
        args: List[FilterExpression],
        kwargs: Dict[str, FilterExpression],
        tag_name: str,
    ) -> None:
        self.nodelist = nodelist
        self.user = self.get_user(args, kwargs, tag_name)
        self.tag_name = tag_name

    @staticmethod
    def get_user(
        args: List[FilterExpression], kwargs: Dict[str, FilterExpression], tag_name: str
    ) -> FilterExpression | None:
        """
        Get the user object from the arguments and
        keyword arguments passed to the utz template tag.
        """
        if args:
            if len(args) != 1:
                raise TemplateSyntaxError(
                    f"{tag_name} requires exactly one argument. The user object\
                    whose timezone is to be used in rendering the template content."
                )
            user = args[0]
        else:
            user = kwargs.get("user", None)
        return user

    def render(self, context) -> SafeText:
        request_user = context.get("request").user
        preferred_user = self.user.resolve(context) if self.user else None
        user = preferred_user if preferred_user else request_user

        try:
            user_model_is_decorated = get_user_model_config(
                type(user), "_decorated", False
            )
        except AttributeError:
            user_model_is_decorated = False

        if user.is_authenticated and user_model_is_decorated:
            tz = user.utz
            original_timezone = timezone.get_current_timezone()
            try:
                timezone.activate(tz)
                output = self.nodelist.render(context)
            finally:
                timezone.activate(original_timezone)
        else:
            output = self.nodelist.render(context)

        return output


@register.tag(name=_generic_name)
def utz_tag(parser: Parser, token: Token) -> UTZNode:
    """
    Template tag to render datetimes in the template content
    in the preferred user's timezone.

    #### In your template:
    To render datetimes in the template content in the timezone
    of the user object passed as an argument:
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
    nodelist = parser.parse(parse_until=(f"end{_generic_name}",))
    parser.delete_first_token()
    return UTZNode(nodelist, args, kwargs, tag_name)


@register.filter(name=_generic_name)
def utz_filter(
    value: datetime.datetime, user: Optional[UserModelUTZMixin] = None
) -> datetime.datetime | utzdatetime:
    """
    Filter to convert a datetime object to the request/provided user's timezone.

    If the user is not authenticated or the user model is not a subclass of UTZUserModelMixin,
    the value is returned as is.

    #### In your template:
    ```
    {% load utz %}
    {{ datetime_object|usertimezone }}
    ```
    A specific user whose timezone would be used, can also be provided:
    ```
    {% load utz %}
    {{ datetime_object|usertimezone:user }}
    ```
    """
    if not user:  # If no user is provided, use the request user
        user = get_request_user()

    try:
        is_decorated = get_user_model_config(type(user), "_decorated", False)
    except AttributeError:
        is_decorated = False

    # If the user model was not decorated with the `usermodel` decorator, return the value as is
    if not is_decorated:
        return value
    try:
        return user.to_local_timezone(value)
    except Exception:
        return value
